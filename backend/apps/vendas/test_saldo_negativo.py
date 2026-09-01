from decimal import Decimal

from rest_framework.test import APITestCase

from apps.cadpro.models import CADProPropriedade
from apps.graos.models import LoteGraos, MovimentacaoGraos, PosicaoSaldoGraos
from apps.graos.services import (
    CapacidadeArmazemExcedidaError, SaldoGraosInsuficienteError,
    creditar_producao, reconciliar_posicao, reservar_saldo,
)
from apps.graos.tests import GraosSaldoBase
from .models import VendaGraos


class VendaSemEntradaTests(GraosSaldoBase, APITestCase):
    def setUp(self):
        self.criar_contexto()
        self.client.force_authenticate(self.usuario)
        self.url = '/api/comercial/vendas/registrar-saida/'
        self.dados = {
            'numero_contrato': 'CONTRATO-NEGATIVO', 'cliente_nome': 'Cliente teste',
            'quantidade_kg': '300', 'data_contrato': '2026-08-31',
            'nova_posicao': {
                'propriedade': self.propriedade.pk, 'cad_pro': str(self.cad_pro.pk),
                'cultura': 'Soja', 'safra': '2026/2027',
                'classificacao_codigo': 'PADRAO', 'armazem': self.armazem.pk,
            },
        }

    def enviar(self, dados=None, chave='sem-entrada'):
        return self.client.post(self.url, dados or self.dados, format='json', HTTP_IDEMPOTENCY_KEY=chave)

    def saldo(self, esperado, comprometido='0'):
        posicao = PosicaoSaldoGraos.objects.get()
        self.assertEqual(posicao.saldo_fisico_kg, Decimal(esperado))
        self.assertEqual(posicao.saldo_comprometido_kg, Decimal(comprometido))
        return posicao

    def lancar(self):
        resposta = self.enviar()
        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.saldo('-300')
        return resposta.data

    def alterar(self, venda, metodo, caminho='', **dados):
        atual = VendaGraos.objects.get(pk=venda['id'])
        return getattr(self.client, metodo)(f"/api/comercial/vendas/{atual.pk}/{caminho}",
            {'versao': atual.versao, 'motivo': 'Correção de teste', **dados},
            format='json', HTTP_IDEMPOTENCY_KEY=f'{metodo}:{caminho}:{atual.versao}')

    def test_inicia_posicao_sem_credito_ficticio_e_replay_nao_duplica(self):
        self.lote.delete()  # Somente fixture vazia: cobre criação sem qualquer lote prévio.
        venda = self.lancar()
        self.assertEqual(self.enviar().data['id'], venda['id'])
        self.assertEqual(LoteGraos.objects.count(), 1)
        self.assertEqual(VendaGraos.objects.count(), 1)
        self.assertEqual(MovimentacaoGraos.objects.count(), 2)
        self.assertFalse(MovimentacaoGraos.objects.filter(delta_fisico_kg__gt=0).exists())
        self.assertEqual(self.enviar({**self.dados, 'quantidade_kg': '301'}).status_code, 409)
        self.saldo('-300')

    def test_entrada_parcial_compensa_negativo_e_reconciliacao_preserva_ledger(self):
        self.lancar()
        self.creditar('100', 'entrada-parcial')
        posicao = self.saldo('-200')
        PosicaoSaldoGraos.objects.filter(pk=posicao.pk).update(saldo_fisico_kg=0)
        reconciliar_posicao(usuario=self.usuario, posicao=posicao, chave_idempotencia='reconciliar')
        self.saldo('-200')
        self.creditar('250', 'entrada-final')
        self.saldo('50')

    def test_reserva_generica_nao_pode_agravar_deficit(self):
        self.lancar()
        with self.assertRaises(SaldoGraosInsuficienteError):
            reservar_saldo(usuario=self.usuario, lote=self.lote, quantidade_kg='1', chave_idempotencia='generica')
        self.saldo('-300')

    def test_devolucao_edicao_exclusao_com_saldo_negativo(self):
        venda = self.lancar()
        resposta = self.alterar(venda, 'post', 'devolver/', quantidade_kg='50')
        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.saldo('-250')
        devolucao = resposta.data['devolucoes'][0]['id']
        resposta = self.alterar(venda, 'patch', f'devolucoes/{devolucao}/', quantidade_kg='80')
        self.assertEqual(resposta.status_code, 200, resposta.data)
        self.saldo('-220')
        entrega = venda['entregas'][0]['id']
        resposta = self.alterar(venda, 'patch', f'entregas/{entrega}/', quantidade_kg='250')
        self.assertEqual(resposta.status_code, 200, resposta.data)
        self.saldo('-170', '50')
        resposta = self.alterar(venda, 'delete')
        self.assertEqual(resposta.status_code, 200, resposta.data)
        self.saldo('0')

    def test_cancelamento_libera_reserva_mesmo_com_disponivel_negativo(self):
        resposta = self.client.post('/api/comercial/vendas/', self.dados, format='json', HTTP_IDEMPOTENCY_KEY='rascunho')
        self.assertEqual(resposta.status_code, 201, resposta.data)
        venda = resposta.data
        self.assertEqual(self.alterar(venda, 'post', 'confirmar/').status_code, 200)
        self.saldo('0', '300')
        self.assertEqual(self.alterar(venda, 'post', 'cancelar/').status_code, 200)
        self.saldo('0')

    def test_deficit_nao_libera_capacidade_ocupada_por_outra_posicao(self):
        self.lancar()
        outra = LoteGraos.objects.create(codigo='OUTRO-PRODUTO', propriedade=self.propriedade,
            cad_pro=self.cad_pro, armazem=self.armazem, cultura='Milho', safra=self.lote.safra,
            classificacao_codigo='PADRAO')
        creditar_producao(usuario=self.usuario, lote=outra, quantidade_kg='2000', chave_idempotencia='encher')
        self.creditar('300', 'compensar')  # Compensar déficit não ocupa espaço.
        with self.assertRaises(CapacidadeArmazemExcedidaError):
            self.creditar('1', 'exceder')
        resposta = self.enviar({**self.dados, 'quantidade_kg': '100'}, chave='segunda-venda')
        self.assertEqual(resposta.status_code, 201, resposta.data)
        resposta = self.alterar(resposta.data, 'delete')
        self.assertEqual(resposta.status_code, 200, resposta.data)
        self.assertEqual(PosicaoSaldoGraos.objects.get(cultura='Soja').saldo_fisico_kg, Decimal('0'))

    def test_vinculo_invalido_e_erro_de_entrega_revertem_contexto_inteiro(self):
        self.lote.delete()
        resposta = self.enviar({**self.dados, 'placa': 'ABC'})
        self.assertEqual(resposta.status_code, 409, resposta.data)
        self.assertFalse(LoteGraos.objects.exists())
        self.assertFalse(PosicaoSaldoGraos.objects.exists())
        self.assertFalse(VendaGraos.objects.exists())
        CADProPropriedade.objects.filter(cad_pro=self.cad_pro).update(ativo=False)
        resposta = self.enviar()
        self.assertEqual(resposta.status_code, 409, resposta.data)
        self.assertFalse(LoteGraos.objects.exists())

    def test_nova_posicao_exige_autenticacao_e_origem_unica(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.enviar().status_code, 401)
        self.client.force_authenticate(self.usuario)
        self.creditar('1')
        resposta = self.enviar({**self.dados, 'posicao': PosicaoSaldoGraos.objects.get().pk})
        self.assertEqual(resposta.status_code, 400)

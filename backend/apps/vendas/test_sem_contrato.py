from decimal import Decimal

from rest_framework.test import APITestCase

from apps.graos.models import MovimentacaoGraos
from .models import ContratoComercial, EntregaVendaGraos, VendaGraos
from .test_saida_completa import SaidaCompletaMixin


class VendaSemContratoTests(SaidaCompletaMixin, APITestCase):
    def setUp(self):
        self.contexto_saida()
        self.client.force_authenticate(self.usuario)
        self.dados.pop('contrato')
        self.dados['quantidade_kg'] = '1200'

    def enviar(self, dados=None, chave='sem-contrato'):
        return self.client.post(self.url, dados or self.dados, format='json', HTTP_IDEMPOTENCY_KEY=chave)

    def test_venda_sem_contrato_usa_destino_e_debita_inclusive_negativo(self):
        resposta = self.enviar()
        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.assertIsNone(resposta.data['contrato'])
        self.assertEqual(resposta.data['numero_contrato'], '')
        self.assertEqual(resposta.data['cliente_nome'], 'Unidade compradora')
        self.assertEqual(resposta.data['status'], 'entregue')
        self.assertEqual(ContratoComercial.objects.count(), 1)  # Apenas a fixture preexistente.
        self.posicao.refresh_from_db()
        self.assertEqual(self.posicao.saldo_fisico_kg, Decimal('-200'))
        venda = VendaGraos.objects.get()
        venda.full_clean()
        self.assertEqual(self.enviar().data['id'], venda.pk)
        self.assertEqual(EntregaVendaGraos.objects.count(), 1)
        resposta = self.enviar({**self.dados, 'destino': 'Outro comprador'})
        self.assertEqual(resposta.status_code, 409, resposta.data)

    def test_aceita_numero_vazio_e_contrato_null(self):
        resposta = self.enviar({**self.dados, 'contrato': None, 'numero_contrato': '', 'cliente_nome': ''})
        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.assertEqual(resposta.data['numero_contrato'], '')

    def test_falta_de_comprador_nao_lanca_movimentos(self):
        antes = MovimentacaoGraos.objects.count()
        resposta = self.enviar({**self.dados, 'destino': '  '})
        self.assertEqual(resposta.status_code, 400, resposta.data)
        self.assertFalse(VendaGraos.objects.exists())
        self.assertEqual(MovimentacaoGraos.objects.count(), antes)

    def test_rascunho_sem_contrato_e_correcao_posterior(self):
        dados = {'posicao': self.posicao.pk, 'cliente_nome': 'Comprador avulso', 'quantidade_kg': '200'}
        resposta = self.client.post('/api/comercial/vendas/', dados, format='json', HTTP_IDEMPOTENCY_KEY='rascunho-avulso')
        self.assertEqual(resposta.status_code, 201, resposta.data)
        venda = resposta.data
        resposta = self.client.patch(f"/api/comercial/vendas/{venda['id']}/", {
            'versao': venda['versao'], 'motivo': 'Corrigir comprador', 'cliente_nome': 'Comprador corrigido',
        }, format='json', HTTP_IDEMPOTENCY_KEY='editar-avulso')
        self.assertEqual(resposta.status_code, 200, resposta.data)
        self.assertEqual(resposta.data['cliente_nome'], 'Comprador corrigido')
        self.assertEqual(resposta.data['numero_contrato'], '')
        self.posicao.refresh_from_db()
        self.assertEqual(self.posicao.saldo_fisico_kg, Decimal('1000'))

    def test_venda_sem_contrato_entregue_pode_ser_corrigida_e_excluida(self):
        resposta = self.enviar()
        venda = resposta.data
        url = f"/api/comercial/vendas/{venda['id']}/"
        resposta = self.client.patch(url, {'versao': venda['versao'], 'motivo': 'Corrigir observação', 'observacoes': 'Venda avulsa'}, format='json', HTTP_IDEMPOTENCY_KEY='correcao')
        self.assertEqual(resposta.status_code, 200, resposta.data)
        resposta = self.client.delete(url, {'versao': resposta.data['versao'], 'motivo': 'Cancelar venda avulsa'}, format='json', HTTP_IDEMPOTENCY_KEY='exclusao')
        self.assertEqual(resposta.status_code, 200, resposta.data)
        self.posicao.refresh_from_db()
        self.assertEqual(self.posicao.saldo_fisico_kg, Decimal('1000'))

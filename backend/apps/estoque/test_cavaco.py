from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import CargaCavaco


class CavacoTests(APITestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user('cavaco', password='teste')
        self.client.force_authenticate(self.usuario)
        self.url = reverse('cavaco-list')
        self.dados = dict(data='2026-07-02', motorista='MARCOS', fornecedor='SILVINHO',
                          valor_tonelada='300.00', peso_bruto='54380.000', tara='21340.000', pago=True)

    def criar(self, **extra):
        response = self.client.post(self.url, {**self.dados, **extra}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def test_calculos_e_persistencia(self):
        carga = self.criar(peso_liquido='1', total='1')
        self.assertEqual(carga['peso_liquido'], '33040.000')
        self.assertEqual(carga['total'], '9912.00')
        self.assertEqual(CargaCavaco.objects.get(pk=carga['id']).total, Decimal('9912.00'))

    def test_arredondamento_monetario(self):
        carga = self.criar(peso_bruto='1001.000', tara='1000.000', valor_tonelada='5.00')
        self.assertEqual(carga['total'], '0.01')

    def test_rejeita_pesos_e_valores_invalidos(self):
        for extra in [dict(tara='54380'), dict(tara='60000'), dict(tara='-1'),
                      dict(peso_bruto='0'), dict(valor_tonelada='-1'), dict(motorista=' '),
                      dict(fornecedor=' '), dict(data='invalida')]:
            with self.subTest(extra=extra):
                self.assertEqual(self.client.post(self.url, {**self.dados, **extra}, format='json').status_code, 400)

    def test_edicao_parcial_revalida_pesos_e_pagamento(self):
        carga = self.criar()
        url = reverse('cavaco-detail', args=[carga['id']])
        self.assertEqual(self.client.patch(url, {'tara': '60000'}).status_code, 400)
        response = self.client.patch(url, {'pago': False, 'tara': '20000'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['pago'])
        self.assertEqual(response.data['total'], '10314.00')

    def test_filtros_busca_pagamento_periodo(self):
        self.criar()
        self.criar(data='2026-08-01', fornecedor='OUTRO', pago=False)
        self.assertEqual(len(self.client.get(self.url, {'search': 'silvinho', 'pago': 'true', 'data_fim': '2026-07-31'}).data), 1)
        self.assertEqual(len(self.client.get(self.url, {'pago': 'false', 'data_inicio': '2026-08-01'}).data), 1)
        self.assertEqual(self.client.get(self.url, {'data_inicio': 'erro'}).status_code, 400)
        self.assertEqual(self.client.get(self.url, {'data_inicio': '2026-09-01', 'data_fim': '2026-08-01'}).status_code, 400)

    def test_romaneio_duas_vias_mesma_carga_escape_e_a4(self):
        carga = self.criar(motorista='<script>alert(1)</script>', observacoes='<img src=x onerror=alert(1)>')
        response = self.client.get(reverse('cavaco-romaneio', args=[carga['id']]))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertEqual(html.count('class="via"'), 2)
        self.assertEqual(html.count(f'{carga["id"]:06d}'), 2)
        self.assertIn('size: A4 portrait', html)
        self.assertIn('1ª VIA', html)
        self.assertIn('2ª VIA', html)
        self.assertNotIn('<script>alert(1)</script>', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertNotIn('<img src=x', html)
        self.assertIn('no-store', response['Cache-Control'])

    def test_exige_autenticacao(self):
        carga = self.criar()
        self.client.force_authenticate(None)
        for url in [self.url, reverse('cavaco-detail', args=[carga['id']]), reverse('cavaco-romaneio', args=[carga['id']])]:
            self.assertIn(self.client.get(url).status_code, (401, 403))
        self.assertIn(self.client.post(self.url, self.dados).status_code, (401, 403))

    def test_banco_protege_integridade(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            CargaCavaco.objects.create(**{**self.dados, 'peso_bruto': Decimal('1'), 'tara': Decimal('2')})

    def test_permissoes_separam_consulta_cadastro_edicao_e_impressao(self):
        from apps.accounts.models import AcessoUsuario
        carga = self.criar()
        acesso = AcessoUsuario.objects.create(usuario=self.usuario, modulos=['cavaco'], permissoes={'cavaco': ['consultar']})
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.assertEqual(self.client.post(self.url, self.dados).status_code, 403)
        self.assertEqual(self.client.patch(reverse('cavaco-detail', args=[carga['id']]), {'pago': False}).status_code, 403)
        self.assertEqual(self.client.delete(reverse('cavaco-detail', args=[carga['id']])).status_code, 403)
        url = reverse('cavaco-romaneio', args=[carga['id']])
        self.assertEqual(self.client.get(url).status_code, 403)
        acesso.permissoes = {'cavaco': ['consultar', 'imprimir']}
        acesso.save()
        self.assertEqual(self.client.get(url).status_code, 200)
        acesso.modulos = ['estoque']
        acesso.save()
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_auditoria_identifica_modulo_e_pesagem(self):
        from apps.core.models import RegistroAlteracao
        carga = self.criar()
        registro = RegistroAlteracao.objects.filter(registro_id=str(carga['id']), modulo='cavaco').last()
        self.assertIsNotNone(registro)
        self.assertIn('peso bruto', registro.alteracoes)
        self.assertIn('tara', registro.alteracoes)
        self.assertNotIn('observacoes', registro.alteracoes)

    def test_exclusao_preserva_registro_e_auditoria_e_oculta_romaneio(self):
        from apps.core.models import RegistroAlteracao
        carga = self.criar()
        url = reverse('cavaco-detail', args=[carga['id']])
        self.assertEqual(self.client.delete(url).status_code, 204)
        registro = CargaCavaco.objects.get(pk=carga['id'])
        self.assertIsNotNone(registro.excluido_em)
        self.assertEqual(registro.total, Decimal('9912.00'))
        self.assertEqual(self.client.get(self.url).data, [])
        self.assertEqual(self.client.get(self.url, {'excluidas': 'true'}).data[0]['id'], carga['id'])
        self.assertEqual(self.client.patch(url, {'pago': False}).status_code, 404)
        self.assertEqual(self.client.delete(url).status_code, 404)
        self.assertEqual(self.client.get(reverse('cavaco-romaneio', args=[carga['id']])).status_code, 404)
        self.assertTrue(RegistroAlteracao.objects.filter(modulo='cavaco', registro_id=str(carga['id']), alteracoes__has_key='excluido em').exists())

    def test_usuario_com_exclusao_pode_excluir_sem_editar(self):
        from apps.accounts.models import AcessoUsuario
        carga = self.criar()
        AcessoUsuario.objects.create(usuario=self.usuario, modulos=['cavaco'], permissoes={'cavaco': ['consultar', 'excluir']})
        url = reverse('cavaco-detail', args=[carga['id']])
        self.assertEqual(self.client.patch(url, {'pago': False}).status_code, 403)
        self.assertEqual(self.client.delete(url).status_code, 204)

    def test_financeiro_pendente_preserva_marcacao_original_e_vencimento_editavel(self):
        from apps.financeiro.models import LancamentoFinanceiro
        carga = self.criar(pago=True)
        conta = LancamentoFinanceiro.objects.get(pk=carga['conta_pagar'])
        self.assertTrue(carga['pago'])
        self.assertEqual(carga['pagamento_financeiro'], 'pendente')
        self.assertEqual(conta.valor, Decimal('9912.00'))
        self.assertEqual(str(conta.data_vencimento), '2026-07-02')
        response = self.client.patch(reverse('cavaco-detail', args=[carga['id']]), {'data_vencimento':'2026-10-30'}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        conta.refresh_from_db()
        self.assertEqual(str(conta.data_vencimento), '2026-10-30')
        self.assertEqual(LancamentoFinanceiro.objects.filter(carga_cavaco_origem__pk=carga['id']).count(), 1)

    def test_exclusao_cancela_conta_pendente_e_liquidacao_bloqueia_alteracao(self):
        from apps.financeiro.models import LancamentoFinanceiro
        from apps.financeiro.services import liquidar_lancamento
        from datetime import date
        carga = self.criar()
        conta = LancamentoFinanceiro.objects.get(pk=carga['conta_pagar'])
        liquidar_lancamento(conta, data_liquidacao=date(2026, 7, 2), valor_liquidado='9912.00')
        url = reverse('cavaco-detail', args=[carga['id']])
        self.assertEqual(self.client.delete(url).status_code, 400)
        self.assertEqual(self.client.patch(url, {'valor_tonelada':'400'}).status_code, 400)
        self.assertIsNone(CargaCavaco.objects.get(pk=carga['id']).excluido_em)
        self.assertEqual(self.client.get(url).data['pagamento_financeiro'], 'liquidado')
        outra = self.criar()
        self.assertEqual(self.client.delete(reverse('cavaco-detail', args=[outra['id']])).status_code, 204)
        self.assertEqual(LancamentoFinanceiro.objects.get(pk=outra['conta_pagar']).status, 'cancelado')

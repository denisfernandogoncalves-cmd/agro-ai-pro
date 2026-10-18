from datetime import date
from decimal import Decimal
from django.test import SimpleTestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from apps.accounts.models import AcessoUsuario
from apps.core.dias_uteis import vencimento_dia_util
from apps.financeiro.models import LancamentoFinanceiro
from apps.financeiro.services import liquidar_lancamento
from .models import CompraDiesel


class VencimentoUtilTests(SimpleTestCase):
    def test_dias_corridos_e_dia_util_mantido(self):
        self.assertEqual(vencimento_dia_util(date(2026, 10, 8), 15), date(2026, 10, 23))

    def test_fim_de_semana_e_feriado_seguidos(self):
        self.assertEqual(vencimento_dia_util(date(2026, 10, 9), 1), date(2026, 10, 13))
        self.assertEqual(vencimento_dia_util(date(2026, 11, 19), 1), date(2026, 11, 23))

    def test_paixao_de_cristo_e_virada_de_ano(self):
        self.assertEqual(vencimento_dia_util(date(2026, 4, 2), 1), date(2026, 4, 6))
        self.assertEqual(vencimento_dia_util(date(2026, 12, 31), 1), date(2027, 1, 4))

    def test_ponto_facultativo_nao_e_feriado_nacional(self):
        self.assertEqual(vencimento_dia_util(date(2026, 2, 16), 0), date(2026, 2, 16))
        self.assertIsNone(vencimento_dia_util(date(2026, 10, 8), None))


class DieselFinanceiroTests(APITestCase):
    url = '/api/transportes/compras-diesel/'

    def setUp(self):
        user = get_user_model().objects.create_user('diesel_financeiro', password='teste')
        AcessoUsuario.objects.create(usuario=user, modulos=['transportes', 'financeiro'])
        self.client.force_authenticate(user)

    def criar(self):
        r = self.client.post(self.url, dict(data='2026-10-09', prazo_dias=1, fornecedor='GP', produtor='NEI', tipo='S10', litros='100', valor_unitario='7.12'), format='json')
        self.assertEqual(r.status_code, 201, r.data)
        return r.data

    def test_previa_valida_e_sem_media(self):
        r = self.client.get(self.url+'vencimento/', {'data': '2026-10-09', 'prazo_dias': 1})
        self.assertEqual(str(r.data['vencimento']), '2026-10-13')
        for p in [{'data': 'erro', 'prazo_dias': 1}, {'data': '2026-10-09', 'prazo_dias': -1}, {'data': '9999-12-31', 'prazo_dias': 1}]:
            self.assertEqual(self.client.get(self.url+'vencimento/', p).status_code, 400)
        self.assertNotIn('preco_medio', self.client.get(self.url+'resumo/').data)

    def test_cria_titulo_unico_e_atualiza_pendente(self):
        compra = self.criar()
        conta = LancamentoFinanceiro.objects.get(pk=compra['conta_pagar'])
        self.assertEqual(conta.valor, Decimal('712.00'))
        self.assertEqual(conta.data_vencimento, date(2026, 10, 13))
        self.assertEqual(conta.status, 'pendente')
        r = self.client.patch(self.url+str(compra['id'])+'/', {'litros':'200','atualizado_em_original':compra['atualizado_em']}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        conta.refresh_from_db()
        self.assertEqual(conta.valor, Decimal('1424.00'))
        self.assertEqual(LancamentoFinanceiro.objects.count(), 1)
        from .diesel_financeiro import sincronizar_conta_diesel
        sincronizar_conta_diesel(CompraDiesel.objects.get(pk=compra['id']))
        self.assertEqual(LancamentoFinanceiro.objects.count(), 1)

    def test_excluir_cancela_titulo_sem_remover_historico(self):
        compra = self.criar()
        r = self.client.delete(self.url+str(compra['id'])+'/', {'atualizado_em_original':compra['atualizado_em']}, format='json')
        self.assertEqual(r.status_code, 204, r.data)
        self.assertEqual(LancamentoFinanceiro.objects.get(pk=compra['conta_pagar']).status, 'cancelado')

    def test_liquidado_nao_e_recalculado_nem_excluido(self):
        compra = self.criar()
        conta = LancamentoFinanceiro.objects.get(pk=compra['conta_pagar'])
        liquidar_lancamento(conta, data_liquidacao=date(2026, 10, 13), valor_liquidado='712')
        url = self.url+str(compra['id'])+'/'
        self.assertEqual(self.client.patch(url, {'litros':'200','atualizado_em_original':compra['atualizado_em']}, format='json').status_code, 400)
        self.assertEqual(self.client.delete(url, {'atualizado_em_original':compra['atualizado_em']}, format='json').status_code, 400)
        obj = CompraDiesel.objects.get(pk=compra['id'])
        self.assertIsNone(obj.excluido_em)
        self.assertEqual(obj.litros, Decimal('100'))

    def test_financeiro_nao_altera_campos_da_origem(self):
        compra = self.criar()
        conta = LancamentoFinanceiro.objects.get(pk=compra['conta_pagar'])
        from apps.financeiro.serializers import LancamentoFinanceiroSerializer
        ser = LancamentoFinanceiroSerializer(conta, data={'valor': '1'}, partial=True)
        self.assertFalse(ser.is_valid())

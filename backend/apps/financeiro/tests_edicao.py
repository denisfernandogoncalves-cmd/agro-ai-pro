from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from .models import LancamentoFinanceiro, ParcelamentoFinanceiro


class EdicaoExclusaoLancamentoTests(APITestCase):
    def setUp(self):
        self.client.force_authenticate(get_user_model().objects.create_user(username="editor-financeiro"))
        grupo = ParcelamentoFinanceiro.objects.create(assinatura="teste")
        self.item = LancamentoFinanceiro.objects.create(
            tipo="pagar", descricao="Boleto teste", valor="100.00",
            recebedor_nome="Fornecedor", data_emissao=date(2026, 9, 1),
            data_vencimento=date(2026, 10, 1), parcela_numero=1,
            total_boletos=2, parcelamento=grupo,
        )
        self.outro = LancamentoFinanceiro.objects.create(
            tipo="pagar", descricao="Segundo boleto", valor="100.00",
            data_vencimento=date(2026, 11, 1), parcela_numero=2,
            total_boletos=2, parcelamento=grupo,
        )
        self.url = f"/api/financeiro/lancamentos/{self.item.pk}/"

    def test_edita_apenas_boleto_escolhido_e_atualiza_resumo(self):
        resposta = self.client.patch(self.url, {
            "descricao": "Descrição corrigida", "recebedor_nome": "Fornecedor corrigido",
            "valor": "125.50", "data_vencimento": "2026-10-15", "observacoes": "Revisado",
        }, format="json")
        self.assertEqual(resposta.status_code, 200, resposta.data)
        self.item.refresh_from_db()
        self.outro.refresh_from_db()
        self.assertEqual(self.item.valor, Decimal("125.50"))
        self.assertEqual(self.item.parcela_numero, 1)
        self.assertEqual(self.item.total_boletos, 2)
        self.assertEqual(self.outro.valor, Decimal("100.00"))
        self.assertEqual(self.outro.descricao, "Segundo boleto")
        resumo = self.client.get("/api/financeiro/lancamentos/resumo/")
        self.assertEqual(Decimal(resumo.data["a_pagar"]), Decimal("225.50"))

    def test_edicao_liquidado_preserva_pagamento(self):
        self.item.status = "liquidado"
        self.item.data_liquidacao = date(2026, 9, 20)
        self.item.valor_liquidado = Decimal("98.00")
        self.item.save()
        resposta = self.client.patch(self.url, {"descricao": "Corrigido", "valor": "110.00"}, format="json")
        self.assertEqual(resposta.status_code, 200, resposta.data)
        self.item.refresh_from_db()
        self.assertEqual(self.item.valor_liquidado, Decimal("98.00"))
        self.assertEqual(self.item.data_liquidacao, date(2026, 9, 20))
        self.assertEqual(self.item.status, "liquidado")

    def test_edicao_invalida_nao_modifica_registro(self):
        resposta = self.client.patch(self.url, {"valor": "-1", "descricao": "Inválido"}, format="json")
        self.assertEqual(resposta.status_code, 400)
        self.item.refresh_from_db()
        self.assertEqual(self.item.descricao, "Boleto teste")
        self.assertEqual(self.item.valor, Decimal("100.00"))

    def test_exclusao_preserva_demais_boletos_e_recalcula_resumo(self):
        resposta = self.client.delete(self.url)
        self.assertEqual(resposta.status_code, 204)
        self.assertFalse(LancamentoFinanceiro.objects.filter(pk=self.item.pk).exists())
        self.assertTrue(LancamentoFinanceiro.objects.filter(pk=self.outro.pk).exists())
        resumo = self.client.get("/api/financeiro/lancamentos/resumo/")
        self.assertEqual(Decimal(resumo.data["a_pagar"]), Decimal("100.00"))

    def test_exclusao_liquidado_atualiza_totais_realizados(self):
        self.item.status = "liquidado"
        self.item.data_liquidacao = date(2026, 9, 20)
        self.item.valor_liquidado = Decimal("100.00")
        self.item.save()
        self.assertEqual(self.client.delete(self.url).status_code, 204)
        resumo = self.client.get("/api/financeiro/lancamentos/resumo/")
        self.assertEqual(Decimal(resumo.data["saidas_realizadas"]), Decimal("0"))

    def test_edicao_e_exclusao_exigem_autenticacao(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.patch(self.url, {"descricao": "Intruso"}).status_code, 401)
        self.assertEqual(self.client.delete(self.url).status_code, 401)
        self.assertTrue(LancamentoFinanceiro.objects.filter(pk=self.item.pk).exists())

import uuid
from decimal import Decimal
from unittest.mock import patch
from rest_framework.test import APITestCase
from apps.financeiro.models import LancamentoFinanceiro
from apps.financeiro.services import liquidar_lancamento
from .test_compras import CompraEstoqueTests
from .models import CompraEstoque, EstornoCompraEstoque
from .compra_financeiro import sincronizar_compra_financeiro
from .services import saldo_lote


class CompraFinanceiroTests(APITestCase):
    setUp = CompraEstoqueTests.setUp

    def criar(self, **dados):
        resposta = self.client.post(self.url, {**self.dados, **dados}, format="json")
        self.assertEqual(resposta.status_code, 201, resposta.data)
        return CompraEstoque.objects.get(pk=self.dados["id"])

    def estornar(self, quantidade, anterior="0", chave=None):
        return self.client.post(f"{self.url}{self.dados['id']}/estornar/", {
            "id": chave or str(uuid.uuid4()), "quantidade": quantidade,
            "quantidade_estornada_original": anterior, "motivo": "Devolução ao fornecedor"}, format="json")

    def test_compra_gera_conta_e_reenvio_nao_duplica(self):
        compra = self.criar()
        self.assertEqual(compra.conta_pagar.valor, Decimal("52910"))
        self.assertEqual(compra.conta_pagar.parceiro, self.fornecedor)
        self.assertEqual(str(compra.conta_pagar.data_vencimento), "2027-07-02")
        self.assertEqual(self.client.post(self.url, self.dados, format="json").status_code, 200)
        self.assertEqual(LancamentoFinanceiro.objects.count(), 1)
        self.assertEqual(self.client.delete(f"{self.url}{compra.pk}/").status_code, 409)

    def test_estorno_reduz_valor_e_quantidade_atomicamente(self):
        compra = self.criar()
        chave = str(uuid.uuid4())
        resposta = self.estornar("15.5", chave=chave)
        self.assertEqual(resposta.status_code, 200, resposta.data)
        self.assertEqual(Decimal(resposta.data["valor_estornado"]), Decimal("1147"))
        self.assertEqual(Decimal(resposta.data["valor_a_pagar"]), Decimal("51763"))
        compra.conta_pagar.refresh_from_db()
        self.assertEqual(compra.conta_pagar.valor, Decimal("51763"))
        self.assertEqual(saldo_lote(compra.movimento.lote), Decimal("699.5"))
        self.assertEqual(self.estornar("15.5", chave=chave).status_code, 200)
        self.assertEqual(LancamentoFinanceiro.objects.count(), 1)

    def test_cancelamento_total_cancela_titulo(self):
        compra = self.criar()
        self.assertEqual(self.estornar("715").status_code, 200)
        compra.conta_pagar.refresh_from_db()
        self.assertEqual(compra.conta_pagar.status, "cancelado")
        self.assertEqual(saldo_lote(compra.movimento.lote), 0)

    def test_compra_paga_gera_creditos_por_estorno_sem_apagar_pagamento(self):
        compra = self.criar()
        from datetime import date
        liquidar_lancamento(compra.conta_pagar, data_liquidacao=date(2026,10,15), valor_liquidado="52910")
        self.assertEqual(self.estornar("15.5").status_code, 200)
        credito = LancamentoFinanceiro.objects.get(tipo="receber")
        self.assertEqual(credito.valor, Decimal("1147"))
        self.assertEqual(credito.status, "pendente")
        self.assertEqual(self.estornar("1", anterior="15.5").status_code, 200)
        self.assertEqual(LancamentoFinanceiro.objects.filter(tipo="receber").count(), 2)
        compra.conta_pagar.refresh_from_db()
        self.assertEqual(compra.conta_pagar.valor_liquidado, Decimal("52910"))
        self.assertEqual(compra.conta_pagar.status, "liquidado")

    def test_falha_financeira_reverte_estorno_e_estoque(self):
        compra = self.criar()
        with patch("apps.estoque.compras.sincronizar_compra_financeiro", side_effect=RuntimeError("falha")):
            with self.assertRaises(RuntimeError):
                self.estornar("10")
        self.assertEqual(saldo_lote(compra.movimento.lote), Decimal("715"))
        self.assertFalse(EstornoCompraEstoque.objects.exists())

    def test_arredondamento_acumulado_e_zero(self):
        compra = self.criar(quantidade_embalagens="7", conteudo_embalagem="3", custo_embalagem="10")
        self.assertEqual(self.estornar("1").status_code, 200)
        self.assertEqual(self.estornar("20", anterior="1").status_code, 200)
        compra.conta_pagar.refresh_from_db()
        self.assertEqual(compra.conta_pagar.status, "cancelado")
        self.assertEqual(self.client.get(f"{self.url}{compra.pk}/").data["valor_liquido"], "0.00")

    def test_reconciliar_compra_existente_idempotente(self):
        compra = self.criar()
        sincronizar_compra_financeiro(compra)
        sincronizar_compra_financeiro(compra)
        self.assertEqual(LancamentoFinanceiro.objects.count(), 1)

    def test_zero_sem_titulo_e_sem_vencimento_com_data_explicita(self):
        compra = self.criar(custo_embalagem="0", data_vencimento=None)
        self.assertIsNone(compra.conta_pagar_id)
        self.assertFalse(LancamentoFinanceiro.objects.exists())

    def test_edicao_direta_do_valor_financeiro_bloqueada(self):
        compra = self.criar()
        resposta = self.client.patch(f"/api/financeiro/lancamentos/{compra.conta_pagar_id}/", {"valor":"1"}, format="json")
        self.assertIn(resposta.status_code, (400,409))
        compra.conta_pagar.refresh_from_db()
        self.assertEqual(compra.conta_pagar.valor, Decimal("52910"))

    def test_estorno_antes_de_pagar_nao_gera_credito_duplicado(self):
        compra = self.criar()
        self.assertEqual(self.estornar("15.5").status_code, 200)
        compra.conta_pagar.refresh_from_db()
        from datetime import date
        liquidar_lancamento(compra.conta_pagar, data_liquidacao=date(2026,10,15), valor_liquidado="51763")
        self.assertEqual(self.estornar("1", anterior="15.5").status_code, 200)
        self.assertEqual(LancamentoFinanceiro.objects.get(tipo="receber").valor, Decimal("74"))

    def test_cancelar_titulo_diretamente_nao_desvincula_compra(self):
        compra = self.criar()
        resposta = self.client.post(f"/api/financeiro/lancamentos/{compra.conta_pagar_id}/cancelar/")
        self.assertEqual(resposta.status_code, 409)
        compra.conta_pagar.refresh_from_db()
        self.assertEqual(compra.conta_pagar.status, "pendente")

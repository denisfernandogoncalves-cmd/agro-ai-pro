import uuid
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.financeiro.models import LancamentoFinanceiro, ParceiroFinanceiro
from .models import CompraEstoque, LoteEstoque, MovimentacaoEstoque, ProdutoEstoque
from .services import saldo_lote


class CompraEstoqueTests(APITestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user("compras-estoque")
        self.client.force_authenticate(self.usuario)
        self.produto = ProdutoEstoque.objects.create(nome="ABADIN 72", categoria="insumo", unidade="l")
        self.fornecedor = ParceiroFinanceiro.objects.create(nome="AGRO PRODUZ", tipo="fornecedor")
        self.url = "/api/estoque/compras/"
        self.dados = {
            "id": str(uuid.uuid4()), "data_compra": "2026-09-14", "produto": self.produto.pk,
            "cultura": "Soja", "quantidade_embalagens": "143", "embalagem": "GL",
            "conteudo_embalagem": "5", "fornecedor": self.fornecedor.pk,
            "custo_embalagem": "370", "data_vencimento": "2027-07-02",
        }

    def test_compra_grava_715_litros_e_vencimento_de_pagamento_separado_da_validade(self):
        resposta = self.client.post(self.url, self.dados, format="json")
        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.assertEqual(resposta.data["quantidade_total"], "715.000")
        self.assertEqual(resposta.data["valor_por_unidade"], "74.0000")
        self.assertEqual(resposta.data["valor_total"], "52910.00")
        compra = CompraEstoque.objects.get()
        self.assertEqual(saldo_lote(compra.movimento.lote), Decimal("715"))
        self.assertEqual(compra.movimento.criado_por, self.usuario)
        self.assertIsNone(compra.movimento.lote.data_validade)
        self.assertEqual(str(compra.data_vencimento), "2027-07-02")
        self.assertFalse(LancamentoFinanceiro.objects.exists())
        self.assertNotIn("produtor", resposta.data)
        self.assertNotIn("assinatura", resposta.data)

    def test_reenvio_nao_duplica_compra_lote_ou_saldo(self):
        self.assertEqual(self.client.post(self.url, self.dados, format="json").status_code, 201)
        self.assertEqual(self.client.post(self.url, self.dados, format="json").status_code, 200)
        self.assertEqual(self.client.post(self.url, {**self.dados, "custo_embalagem": "400"}, format="json").status_code, 409)
        self.assertEqual(CompraEstoque.objects.count(), 1)
        self.assertEqual(LoteEstoque.objects.count(), 1)
        self.assertEqual(MovimentacaoEstoque.objects.count(), 1)

    def test_safra_salva_no_movimento_aparece_na_lista_e_busca(self):
        dados = {**self.dados, "safra": "2026"}
        resposta = self.client.post(self.url, dados, format="json")
        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.assertEqual(resposta.data["safra"], "2026")
        self.assertEqual(MovimentacaoEstoque.objects.get().safra, "2026")
        self.assertEqual(len(self.client.get(self.url, {"search": "2026"}).data), 1)
        self.assertEqual(len(self.client.get(self.url, {"search": "2025"}).data), 0)
        self.assertEqual(self.client.post(self.url, dados, format="json").status_code, 200)
        self.assertEqual(self.client.post(self.url, {**dados, "safra": "2025"}, format="json").status_code, 409)

    def test_safra_opcional_preserva_reenvio_antigo(self):
        from .compras import CompraEntradaSerializer, registrar_compra
        entrada = CompraEntradaSerializer(data=self.dados)
        entrada.is_valid(raise_exception=True)
        dados_antigos = dict(entrada.validated_data)
        dados_antigos.pop("safra")
        registrar_compra(usuario=self.usuario, dados=dados_antigos)
        resposta = self.client.post(self.url, {**self.dados, "safra": ""}, format="json")
        self.assertEqual(resposta.status_code, 200, resposta.data)
        self.assertEqual(resposta.data["safra"], "")
        self.assertEqual(MovimentacaoEstoque.objects.count(), 1)

    def test_valida_cadastros_e_valores_antes_de_gravar(self):
        for alteracao in ({"quantidade_embalagens": "0"}, {"conteudo_embalagem": "0"},
                          {"custo_embalagem": "-1"}, {"custo_embalagem": ""},
                          {"quantidade_embalagens": "0.001", "conteudo_embalagem": "0.001"},
                          {"embalagem": ""}, {"data_vencimento": "invalida"}):
            with self.subTest(alteracao=alteracao):
                self.assertEqual(self.client.post(self.url, {**self.dados, **alteracao}, format="json").status_code, 400)
        self.produto.unidade = "sc"
        self.produto.save()
        self.assertEqual(self.client.post(self.url, self.dados, format="json").status_code, 400)
        self.produto.unidade = "kg"
        self.produto.save()
        self.fornecedor.ativo = False
        self.fornecedor.save()
        self.assertEqual(self.client.post(self.url, self.dados, format="json").status_code, 400)
        self.assertFalse(LoteEstoque.objects.exists())
        self.assertFalse(MovimentacaoEstoque.objects.exists())

    def test_falha_intermediaria_reverte_lote_e_entrada(self):
        with patch.object(CompraEstoque, "save", side_effect=RuntimeError("falha simulada")):
            with self.assertRaises(RuntimeError):
                self.client.post(self.url, self.dados, format="json")
        self.assertFalse(LoteEstoque.objects.exists())
        self.assertFalse(MovimentacaoEstoque.objects.exists())

    def test_lista_busca_edicao_bloqueada_e_exclusao_controlada(self):
        self.client.post(self.url, self.dados, format="json")
        resposta = self.client.get(self.url, {"search": "Soja"})
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(len(resposta.data), 1)
        self.assertEqual(resposta.data[0]["fornecedor_nome"], "AGRO PRODUZ")
        self.assertEqual(len(self.client.get(self.url, {"search": "ausente"}).data), 0)
        detalhe = f"{self.url}{self.dados['id']}/"
        self.assertEqual(self.client.patch(detalhe, {"custo_embalagem": "1"}).status_code, 405)
        self.assertEqual(self.client.delete(detalhe).status_code, 204)
        self.assertFalse(CompraEstoque.objects.filter(pk=self.dados["id"]).exists())
        self.assertFalse(MovimentacaoEstoque.objects.exists())
        self.assertEqual(saldo_lote(LoteEstoque.objects.get()), Decimal("0"))
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(self.url).status_code, 401)
        self.assertEqual(self.client.post(self.url, self.dados, format="json").status_code, 401)

    def test_saida_utiliza_saldo_em_litros_e_nao_quantidade_de_embalagens(self):
        self.client.post(self.url, self.dados, format="json")
        lote = LoteEstoque.objects.get()
        resposta = self.client.post("/api/estoque/movimentacoes/", {"lote": lote.pk, "tipo": "saida", "quantidade": "700"}, format="json")
        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.assertEqual(saldo_lote(lote), Decimal("15"))
        self.assertEqual(self.client.post("/api/estoque/movimentacoes/", {"lote": lote.pk, "tipo": "saida", "quantidade": "16"}, format="json").status_code, 400)

    def test_preserva_total_exato_e_aceita_vencimento_nao_informado(self):
        resposta = self.client.post(self.url, {**self.dados, "quantidade_embalagens": "7", "conteudo_embalagem": "3", "custo_embalagem": "10", "data_vencimento": None}, format="json")
        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.assertEqual(resposta.data["valor_por_unidade"], "3.3333")
        self.assertEqual(resposta.data["valor_total"], "70.00")
        self.assertIsNone(resposta.data["data_vencimento"])

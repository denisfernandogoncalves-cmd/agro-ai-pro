from decimal import Decimal
from uuid import uuid4

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.financeiro.models import ParceiroFinanceiro
from .models import LoteEstoque, MovimentacaoEstoque, ProdutoEstoque
from .services import registrar_movimentacao


class DisponibilidadeTests(APITestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user("consulta-estoque")
        self.client.force_authenticate(self.usuario)
        self.produto = ProdutoEstoque.objects.create(nome="Produto", categoria="insumo", unidade="l")
        self.fornecedor = ParceiroFinanceiro.objects.create(nome="Fornecedor", tipo="fornecedor")
        self.url = "/api/estoque/disponibilidade/"

    def entrada(self, quantidade, custo, data="2026-09-01", lote=None, fornecedor=None):
        lote = lote or LoteEstoque.objects.create(produto=self.produto, fornecedor=fornecedor or self.fornecedor, codigo=str(uuid4()))
        registrar_movimentacao(usuario=self.usuario, lote=lote, tipo="entrada", quantidade=quantidade, custo_unitario=custo, data_movimento=data)
        return lote

    def saida(self, lote, quantidade):
        registrar_movimentacao(usuario=self.usuario, lote=lote, tipo="saida", quantidade=quantidade, data_movimento="2026-09-19")

    def test_saldo_atual_por_data_e_media_ponderada_sem_duplicacao(self):
        primeiro = self.entrada("10", "10")
        self.entrada("30", "20")
        self.entrada("10", "30", "2026-09-02")
        self.saida(primeiro, "4")
        resposta = self.client.get(self.url)
        self.assertEqual(resposta.status_code, 200)
        itens = resposta.data["itens"]
        self.assertEqual(len(itens), 2)
        self.assertEqual(itens[0]["disponivel"], "36.000")
        self.assertEqual(itens[0]["quantidade_comprada"], "40.000")
        self.assertEqual(itens[0]["preco_medio"], "17.5000")
        self.assertEqual(resposta.data["resumo"][0]["disponivel"], "46.000")
        self.assertEqual(resposta.data["resumo"][0]["preco_medio"], "20.0000")

    def test_filtro_data_nao_exclui_saidas_posteriores(self):
        lote = self.entrada("10", "5")
        self.saida(lote, "3")
        self.entrada("20", "7", "2026-09-02")
        itens = self.client.get(self.url, {"data_inicio": "2026-09-01", "data_fim": "2026-09-01"}).data["itens"]
        self.assertEqual(len(itens), 1)
        self.assertEqual(itens[0]["disponivel"], "7.000")

    def test_fornecedores_e_produtos_nao_se_misturam(self):
        outro = ParceiroFinanceiro.objects.create(nome="Outro", tipo="fornecedor")
        self.entrada("10", "5")
        self.entrada("20", "7", fornecedor=outro)
        resposta = self.client.get(self.url, {"fornecedor": outro.pk, "produto": self.produto.pk})
        self.assertEqual(len(resposta.data["itens"]), 1)
        self.assertEqual(resposta.data["itens"][0]["disponivel"], "20.000")
        self.assertEqual(self.client.get(self.url, {"produto": 999999}).data["itens"], [])

    def test_lote_multiplas_datas_nao_inventa_consumo_por_compra(self):
        lote = self.entrada("10", "5")
        self.entrada("20", "8", "2026-09-02", lote=lote)
        self.saida(lote, "5")
        itens = self.client.get(self.url).data["itens"]
        self.assertEqual(len(itens), 1)
        self.assertIsNone(itens[0]["data_compra"])
        self.assertEqual(itens[0]["disponivel"], "25.000")
        self.assertEqual(itens[0]["preco_medio"], "7.0000")
        self.assertEqual(len(itens[0]["lotes"][0]["datas_entrada"]), 2)

    def test_saldo_zero_opcional_e_custo_zero_valido(self):
        lote = self.entrada("10", "0")
        self.saida(lote, "10")
        self.assertEqual(self.client.get(self.url).data["itens"], [])
        item = self.client.get(self.url, {"somente_disponivel": "false"}).data["itens"][0]
        self.assertEqual(item["disponivel"], "0.000")
        self.assertEqual(item["preco_medio"], "0.0000")

    def test_compra_utiliza_valor_total_sem_perda_por_custo_unitario_arredondado(self):
        resposta = self.client.post("/api/estoque/compras/", {
            "id": str(uuid4()), "data_compra": "2026-09-01", "produto": self.produto.pk,
            "fornecedor": self.fornecedor.pk, "quantidade_embalagens": "1", "embalagem": "GL",
            "conteudo_embalagem": "3", "custo_embalagem": "1",
        }, format="json")
        self.assertEqual(resposta.status_code, 201, resposta.data)
        item = self.client.get(self.url).data["itens"][0]
        self.assertEqual(item["valor_aquisicao"], "1.00")
        self.assertEqual(item["preco_medio"], "0.3333")

    def test_validacao_e_autenticacao(self):
        for params in ({"produto": "abc"}, {"data_inicio": "invalida"}, {"data_inicio": "2026-09-20", "data_fim": "2026-09-01"}):
            self.assertEqual(self.client.get(self.url, params).status_code, 400)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(self.url).status_code, 401)

    def test_historico_sem_fornecedor_ou_custo_nao_vira_zero(self):
        lote = LoteEstoque.objects.create(produto=self.produto, codigo="legado")
        MovimentacaoEstoque.objects.create(lote=lote, tipo="entrada", quantidade=Decimal("5"), criado_por=self.usuario)
        item = self.client.get(self.url).data["itens"][0]
        self.assertEqual(item["fornecedor"], "Fornecedor não informado")
        self.assertIsNone(item["preco_medio"])
        self.assertIsNone(item["valor_aquisicao"])

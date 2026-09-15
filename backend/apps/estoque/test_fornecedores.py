from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from rest_framework.test import APITestCase

from apps.financeiro.models import ParceiroFinanceiro
from apps.relatorios.selectors import _estoque_insumos
from .models import LoteEstoque, ProdutoEstoque


class LotesFornecedorTests(APITestCase):
    def setUp(self):
        self.client.force_authenticate(get_user_model().objects.create_user("lotes_fornecedor"))
        self.produto = ProdutoEstoque.objects.create(nome="Semente", categoria="semente", unidade="kg")
        self.fornecedor = ParceiroFinanceiro.objects.create(nome="Fornecedor", tipo="fornecedor")
        self.dados = {"produto": self.produto.pk, "fornecedor": self.fornecedor.pk, "codigo": "L-1"}

    def test_produto_central_fornecedor_e_movimentacao_sem_deposito(self):
        resposta = self.client.post("/api/estoque/lotes/", self.dados, format="json")
        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.assertEqual(resposta.data["produto_nome"], self.produto.nome)
        self.assertEqual(resposta.data["fornecedor_nome"], self.fornecedor.nome)
        self.assertIsNone(resposta.data["local"])
        movimento = self.client.post("/api/estoque/movimentacoes/", {
            "lote": resposta.data["id"], "tipo": "entrada", "quantidade": "10", "custo_unitario": "2",
        }, format="json")
        self.assertEqual(movimento.status_code, 201, movimento.data)
        self.assertEqual(movimento.data["fornecedor_nome"], self.fornecedor.nome)
        posicao = self.client.get("/api/estoque/lotes/posicao/")
        self.assertEqual(posicao.status_code, 200)
        self.assertEqual(posicao.data[0]["fornecedor"], self.fornecedor.nome)
        self.assertEqual(_estoque_insumos({})[0]["local"], "")
        self.assertEqual(self.client.get("/api/estoque/lotes/resumo/").status_code, 200)
        self.assertEqual(self.client.delete(f"/api/financeiro/parceiros/{self.fornecedor.pk}/").status_code, 409)

    def test_rejeita_cliente_inativo_e_produto_inativo(self):
        for alteracao in ({"tipo": "cliente"}, {"tipo": "fornecedor", "ativo": False}):
            ParceiroFinanceiro.objects.filter(pk=self.fornecedor.pk).update(**alteracao)
            resposta = self.client.post("/api/estoque/lotes/", self.dados, format="json")
            self.assertEqual(resposta.status_code, 400, resposta.data)
            self.assertIn("fornecedor", resposta.data)
        ParceiroFinanceiro.objects.filter(pk=self.fornecedor.pk).update(ativo=True, tipo="ambos")
        ProdutoEstoque.objects.filter(pk=self.produto.pk).update(ativo=False)
        self.assertEqual(self.client.post("/api/estoque/lotes/", self.dados, format="json").status_code, 400)

    def test_exige_fornecedor_e_bloqueia_duplicado(self):
        self.assertEqual(self.client.post("/api/estoque/lotes/", {"produto": self.produto.pk, "codigo": "L-1"}).status_code, 400)
        self.assertEqual(self.client.post("/api/estoque/lotes/", self.dados, format="json").status_code, 201)
        self.assertEqual(self.client.post("/api/estoque/lotes/", self.dados, format="json").status_code, 400)
        with self.assertRaises(IntegrityError), transaction.atomic():
            LoteEstoque.objects.create(produto=self.produto, fornecedor=self.fornecedor, codigo="L-1")

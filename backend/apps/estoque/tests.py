from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.propriedades.models import Propriedade

from .models import (
    LocalEstoque,
    LoteEstoque,
    MovimentacaoEstoque,
    ProdutoEstoque,
)
from .services import (
    EstoqueInsuficienteError,
    posicao_estoque,
    registrar_movimentacao,
    resumo_estoque,
    saldo_lote,
)


class EstoqueRegrasTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user("estoquista", password="x")
        self.produto = ProdutoEstoque.objects.create(
            nome="Fertilizante 10-10-10",
            categoria=ProdutoEstoque.Categoria.FERTILIZANTE,
            unidade=ProdutoEstoque.Unidade.KG,
            estoque_minimo="100",
        )
        self.local = LocalEstoque.objects.create(nome="Galpão principal")
        self.lote = LoteEstoque.objects.create(
            produto=self.produto,
            local=self.local,
            codigo="FERT-001",
            data_validade=timezone.localdate() + timedelta(days=15),
        )

    def movimentar(self, tipo, quantidade, custo=None):
        return registrar_movimentacao(
            usuario=self.usuario,
            tipo=tipo,
            lote=self.lote,
            quantidade=quantidade,
            custo_unitario=custo,
            data_movimento=timezone.localdate(),
        )

    def test_entrada_exige_custo(self):
        movimento = MovimentacaoEstoque(
            tipo=MovimentacaoEstoque.Tipo.ENTRADA,
            lote=self.lote,
            quantidade="10",
            criado_por=self.usuario,
        )
        with self.assertRaisesMessage(ValidationError, "custo unitário"):
            movimento.full_clean()

    def test_saldo_soma_entradas_e_subtrai_saidas(self):
        self.movimentar("entrada", "250.500", "4.20")
        self.movimentar("saida", "50.250")
        self.assertEqual(saldo_lote(self.lote), Decimal("200.250"))

    def test_saida_sem_saldo_e_bloqueada(self):
        self.movimentar("entrada", "10", "2")
        with self.assertRaisesMessage(EstoqueInsuficienteError, "Saldo insuficiente"):
            self.movimentar("saida", "10.001")

    def test_lote_e_produto_inativos_nao_recebem_movimentos(self):
        self.lote.ativo = False
        self.lote.save(update_fields=("ativo",))
        with self.assertRaisesMessage(ValueError, "precisam estar ativos"):
            self.movimentar("entrada", "10", "2")

    def test_posicao_identifica_validade_e_estoque_minimo(self):
        self.movimentar("entrada", "80", "2")
        posicao = posicao_estoque()[0]
        self.assertEqual(posicao["saldo"], Decimal("80"))
        self.assertTrue(posicao["vence_em_30_dias"])
        self.assertTrue(posicao["abaixo_minimo"])

    def test_resumo_contabiliza_alertas(self):
        self.movimentar("entrada", "80", "2")
        resumo = resumo_estoque()
        self.assertEqual(resumo["produtos_ativos"], 1)
        self.assertEqual(resumo["lotes_vencendo"], 1)
        self.assertEqual(resumo["itens_abaixo_minimo"], 1)

    def test_movimentos_protegem_lote_de_exclusao(self):
        self.movimentar("entrada", "10", "2")
        with self.assertRaises(ProtectedError):
            self.lote.delete()


class EstoqueApiTests(APITestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user("api_estoque", password="x")
        self.client.force_authenticate(self.usuario)
        self.propriedade = Propriedade.objects.create(
            nome="Fazenda Estoque",
            municipio="Sorriso",
            uf="MT",
            area_hectares="100",
        )
        self.produto = ProdutoEstoque.objects.create(
            nome="Semente de soja",
            categoria=ProdutoEstoque.Categoria.SEMENTE,
            unidade=ProdutoEstoque.Unidade.SC,
            estoque_minimo="20",
        )
        self.local = LocalEstoque.objects.create(
            nome="Depósito norte",
            propriedade=self.propriedade,
        )
        self.lote = LoteEstoque.objects.create(
            produto=self.produto,
            local=self.local,
            codigo="SOJA-26",
            data_validade=timezone.localdate() + timedelta(days=120),
        )

    def test_endpoints_exigem_autenticacao(self):
        self.client.force_authenticate(None)
        for url in (
            "/api/estoque/produtos/",
            "/api/estoque/locais/",
            "/api/estoque/lotes/",
            "/api/estoque/movimentacoes/",
        ):
            self.assertEqual(self.client.get(url).status_code, 401)

    def test_crud_de_cadastros(self):
        produto = self.client.post(
            "/api/estoque/produtos/",
            {
                "nome": "Herbicida seletivo",
                "categoria": "herbicida",
                "unidade": "l",
                "estoque_minimo": "5",
            },
            format="json",
        )
        self.assertEqual(produto.status_code, 201, produto.data)
        local = self.client.post(
            "/api/estoque/locais/",
            {"nome": "Armário de defensivos", "propriedade": self.propriedade.id},
            format="json",
        )
        self.assertEqual(local.status_code, 201)
        lote = self.client.post(
            "/api/estoque/lotes/",
            {
                "produto": produto.data["id"],
                "local": local.data["id"],
                "codigo": "HERB-1",
            },
            format="json",
        )
        self.assertEqual(lote.status_code, 201)

    def test_fluxo_de_entrada_saida_e_rastreabilidade(self):
        entrada = self.client.post(
            "/api/estoque/movimentacoes/",
            {
                "tipo": "entrada",
                "lote": self.lote.id,
                "quantidade": "100",
                "custo_unitario": "150.25",
                "documento_fiscal": "NF-100",
                "propriedade": self.propriedade.id,
                "safra": "2026/2027",
            },
            format="json",
        )
        self.assertEqual(entrada.status_code, 201)
        self.assertEqual(entrada.data["criado_por_nome"], self.usuario.username)
        saida = self.client.post(
            "/api/estoque/movimentacoes/",
            {
                "tipo": "saida",
                "lote": self.lote.id,
                "quantidade": "25",
                "propriedade": self.propriedade.id,
                "safra": "2026/2027",
            },
            format="json",
        )
        self.assertEqual(saida.status_code, 201)
        lista = self.client.get(
            f"/api/estoque/movimentacoes/?search=NF-100&produto={self.produto.id}"
        )
        self.assertEqual(lista.status_code, 200)
        self.assertEqual(len(lista.data), 1)
        posicao = self.client.get("/api/estoque/lotes/posicao/")
        self.assertEqual(posicao.data[0]["saldo"], Decimal("75"))

    def test_movimentos_sao_imutaveis(self):
        entrada = self.client.post(
            "/api/estoque/movimentacoes/",
            {
                "tipo": "entrada",
                "lote": self.lote.id,
                "quantidade": "10",
                "custo_unitario": "1",
            },
            format="json",
        )
        url = f"/api/estoque/movimentacoes/{entrada.data['id']}/"
        self.assertEqual(self.client.patch(url, {"quantidade": "999"}).status_code, 405)
        self.assertEqual(self.client.delete(url).status_code, 405)

    def test_saida_maior_que_saldo_retorna_400(self):
        resposta = self.client.post(
            "/api/estoque/movimentacoes/",
            {
                "tipo": "saida",
                "lote": self.lote.id,
                "quantidade": "1",
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 400)
        self.assertIn("Saldo insuficiente", str(resposta.data))

    def test_exclusao_de_produto_em_uso_retorna_409(self):
        resposta = self.client.delete(f"/api/estoque/produtos/{self.produto.id}/")
        self.assertEqual(resposta.status_code, 409)

    def test_filtros_e_resumo(self):
        resposta = self.client.get(
            "/api/estoque/produtos/?categoria=semente&search=soja&ordering=nome"
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(len(resposta.data), 1)
        resumo = self.client.get("/api/estoque/lotes/resumo/")
        self.assertEqual(resumo.status_code, 200)
        self.assertEqual(resumo.data["produtos_ativos"], 1)

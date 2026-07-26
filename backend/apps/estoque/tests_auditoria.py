from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.propriedades.models import Propriedade

from .models import LocalEstoque, LoteEstoque, MovimentacaoEstoque, ProdutoEstoque
from .services import posicao_estoque, registrar_movimentacao, resumo_estoque


class EstoqueEscopoTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(
            "auditoria_estoque", password="x"
        )
        self.propriedade = Propriedade.objects.create(
            nome="Fazenda A",
            municipio="Ivaiporã",
            uf="PR",
            area_hectares="100",
        )
        self.outra = Propriedade.objects.create(
            nome="Fazenda B",
            municipio="Arapuã",
            uf="PR",
            area_hectares="80",
        )
        self.produto = ProdutoEstoque.objects.create(
            nome="Produto A",
            categoria=ProdutoEstoque.Categoria.INSUMO,
            unidade=ProdutoEstoque.Unidade.KG,
            estoque_minimo="10",
        )
        self.produto_outra = ProdutoEstoque.objects.create(
            nome="Produto B",
            categoria=ProdutoEstoque.Categoria.FERTILIZANTE,
            unidade=ProdutoEstoque.Unidade.KG,
            estoque_minimo="10",
        )
        local = LocalEstoque.objects.create(
            nome="Depósito A", propriedade=self.propriedade
        )
        local_outra = LocalEstoque.objects.create(
            nome="Depósito B", propriedade=self.outra
        )
        self.lote = LoteEstoque.objects.create(
            produto=self.produto,
            local=local,
            codigo="A-1",
        )
        lote_outra = LoteEstoque.objects.create(
            produto=self.produto_outra,
            local=local_outra,
            codigo="B-1",
            data_validade=timezone.localdate(),
        )
        registrar_movimentacao(
            usuario=self.usuario,
            tipo=MovimentacaoEstoque.Tipo.ENTRADA,
            lote=self.lote,
            quantidade="50",
            custo_unitario="2",
            data_movimento=timezone.localdate(),
            propriedade=self.propriedade,
            safra="2026/2027",
        )
        registrar_movimentacao(
            usuario=self.usuario,
            tipo=MovimentacaoEstoque.Tipo.ENTRADA,
            lote=lote_outra,
            quantidade="90",
            custo_unitario="3",
            data_movimento=timezone.localdate(),
            propriedade=self.outra,
            safra="2025/2026",
        )

    def test_posicao_filtra_propriedade_e_safra(self):
        posicoes = posicao_estoque(
            propriedade=self.propriedade.id,
            safra="2026/2027",
        )
        self.assertEqual(len(posicoes), 1)
        self.assertEqual(posicoes[0]["lote_id"], self.lote.id)
        self.assertEqual(posicoes[0]["saldo"], 50)

    def test_posicao_nao_faz_consulta_por_lote(self):
        with self.assertNumQueries(1):
            posicoes = posicao_estoque(propriedade=self.propriedade.id)
        self.assertEqual(len(posicoes), 1)

    def test_resumo_nao_mistura_produtos_de_outra_propriedade(self):
        resumo = resumo_estoque(propriedade=self.propriedade.id)
        self.assertEqual(resumo["produtos_ativos"], 1)
        self.assertEqual(resumo["lotes_com_saldo"], 1)

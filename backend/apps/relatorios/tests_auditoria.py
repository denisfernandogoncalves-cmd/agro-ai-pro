from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.estoque.models import (
    LocalEstoque,
    LoteEstoque,
    MovimentacaoEstoque,
    ProdutoEstoque,
)
from apps.estoque.services import registrar_movimentacao
from apps.propriedades.models import Propriedade

from .services import dashboard_gerencial


class DashboardEscopoTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(
            "auditoria_relatorios", password="x"
        )
        self.propriedade = Propriedade.objects.create(
            nome="Fazenda Relatório A",
            municipio="Ivaiporã",
            uf="PR",
            area_hectares="100",
        )
        self.outra = Propriedade.objects.create(
            nome="Fazenda Relatório B",
            municipio="Arapuã",
            uf="PR",
            area_hectares="100",
        )
        produto = ProdutoEstoque.objects.create(
            nome="Estoque externo",
            categoria=ProdutoEstoque.Categoria.INSUMO,
            unidade=ProdutoEstoque.Unidade.KG,
            estoque_minimo="100",
        )
        local = LocalEstoque.objects.create(
            nome="Depósito externo",
            propriedade=self.outra,
        )
        lote = LoteEstoque.objects.create(
            produto=produto,
            local=local,
            codigo="EXT-1",
            data_validade=timezone.localdate(),
        )
        registrar_movimentacao(
            usuario=self.usuario,
            tipo=MovimentacaoEstoque.Tipo.ENTRADA,
            lote=lote,
            quantidade="10",
            custo_unitario="1",
            data_movimento=timezone.localdate(),
            propriedade=self.outra,
            safra="2026/2027",
        )

    def test_dashboard_filtrado_nao_inclui_estoque_de_outra_propriedade(self):
        dados = dashboard_gerencial(
            propriedade=self.propriedade.id,
            safra="2026/2027",
        )
        self.assertEqual(dados["estoque"]["produtos_ativos"], 0)
        self.assertEqual(dados["estoque"]["lotes_com_saldo"], 0)
        self.assertEqual(dados["estoque"]["itens_abaixo_minimo"], 0)

    def test_propriedade_inexistente_retorna_contagem_zero(self):
        dados = dashboard_gerencial(propriedade=999999)
        self.assertEqual(dados["estrutura"]["propriedades"], 0)


class DashboardFiltrosApiTests(APITestCase):
    def setUp(self):
        usuario = get_user_model().objects.create_user(
            "auditoria_relatorios_api", password="x"
        )
        self.client.force_authenticate(usuario)

    def test_rejeita_identificador_de_propriedade_invalido(self):
        resposta = self.client.get(
            "/api/relatorios/dashboard/?propriedade=nao-numerica"
        )
        self.assertEqual(resposta.status_code, 400)
        self.assertIn("propriedade", resposta.data)

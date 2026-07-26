from datetime import timedelta

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

from .services import gerar_insights


class InsightsEscopoTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(
            "auditoria_insights", password="x"
        )
        self.propriedade = Propriedade.objects.create(
            nome="Fazenda Insights A",
            municipio="Ivaiporã",
            uf="PR",
            area_hectares="100",
        )
        outra = Propriedade.objects.create(
            nome="Fazenda Insights B",
            municipio="Arapuã",
            uf="PR",
            area_hectares="100",
        )
        produto = ProdutoEstoque.objects.create(
            nome="Produto vencido externo",
            categoria=ProdutoEstoque.Categoria.INSUMO,
            unidade=ProdutoEstoque.Unidade.KG,
            estoque_minimo="20",
        )
        local = LocalEstoque.objects.create(
            nome="Depósito externo",
            propriedade=outra,
        )
        lote = LoteEstoque.objects.create(
            produto=produto,
            local=local,
            codigo="VENC-1",
            data_validade=timezone.localdate() - timedelta(days=1),
        )
        registrar_movimentacao(
            usuario=self.usuario,
            tipo=MovimentacaoEstoque.Tipo.ENTRADA,
            lote=lote,
            quantidade="10",
            custo_unitario="1",
            data_movimento=timezone.localdate(),
            propriedade=outra,
            safra="2026/2027",
        )

    def test_insight_nao_mistura_estoque_de_outra_propriedade(self):
        dados = gerar_insights(
            propriedade=self.propriedade.id,
            safra="2026/2027",
        )
        codigos = [item["codigo"] for item in dados["insights"]]
        self.assertEqual(codigos, ["sem_alertas"])


class InsightsFiltrosApiTests(APITestCase):
    def setUp(self):
        usuario = get_user_model().objects.create_user(
            "auditoria_insights_api", password="x"
        )
        self.client.force_authenticate(usuario)

    def test_rejeita_identificador_de_propriedade_invalido(self):
        resposta = self.client.get("/api/ai/insights/?propriedade=invalida")
        self.assertEqual(resposta.status_code, 400)
        self.assertIn("propriedade", resposta.data)

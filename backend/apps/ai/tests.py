from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.financeiro.models import CategoriaFinanceira, LancamentoFinanceiro
from apps.propriedades.models import Propriedade

from .services import gerar_insights


class InsightsBase:
    def dados(self):
        self.usuario = get_user_model().objects.create_user("insights", password="x")
        self.propriedade = Propriedade.objects.create(
            nome="Fazenda Insights", municipio="Sorriso", uf="MT", area_hectares="100"
        )


class InsightsServiceTests(InsightsBase, TestCase):
    def setUp(self): self.dados()

    def test_retorna_informativo_sem_pendencias(self):
        dados = gerar_insights(propriedade=self.propriedade.id)
        self.assertEqual(dados["metodo"], "regras_explicaveis_v1")
        self.assertEqual(dados["insights"][0]["codigo"], "sem_alertas")

    def test_detecta_financeiro_atrasado_com_evidencia(self):
        categoria = CategoriaFinanceira.objects.create(nome="Despesa IA", aplicacao="despesa")
        LancamentoFinanceiro.objects.create(
            tipo="pagar", descricao="Conta", valor="100", categoria=categoria,
            propriedade=self.propriedade,
            data_vencimento=timezone.localdate() - timedelta(days=1),
        )
        insight = gerar_insights(propriedade=self.propriedade.id)["insights"][0]
        self.assertEqual(insight["codigo"], "financeiro_atrasado")
        self.assertIn("1 lançamento", insight["evidencia"])


class InsightsApiTests(InsightsBase, APITestCase):
    def setUp(self):
        self.dados()
        self.client.force_authenticate(self.usuario)

    def test_exige_autenticacao(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/ai/insights/").status_code, 401)

    def test_resposta_tem_aviso_e_metodo(self):
        resposta = self.client.get(f"/api/ai/insights/?propriedade={self.propriedade.id}")
        self.assertEqual(resposta.status_code, 200)
        self.assertIn("Não substitui", resposta.data["aviso"])

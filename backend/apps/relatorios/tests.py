from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.financeiro.models import CategoriaFinanceira, LancamentoFinanceiro
from apps.maquinas.models import Maquina, ManutencaoMaquina
from apps.producao.models import OperacaoAgricola
from apps.propriedades.models import Propriedade
from apps.talhoes.models import Talhao

from .services import dashboard_gerencial


class DashboardBase:
    def dados(self):
        self.usuario = get_user_model().objects.create_user("relatorios", password="x")
        self.propriedade = Propriedade.objects.create(
            nome="Fazenda Relatório", municipio="Sorriso", uf="MT", area_hectares="100"
        )
        self.outra = Propriedade.objects.create(
            nome="Outra Fazenda", municipio="Lucas", uf="MT", area_hectares="50"
        )
        self.talhao = Talhao.objects.create(
            propriedade=self.propriedade, nome="Talhão R", area_hectares="40", safra="2026/2027"
        )
        self.operacao = OperacaoAgricola.objects.create(
            talhao=self.talhao, tipo="plantio", descricao="Plantio", data_planejada=timezone.localdate(),
            area_hectares="40", custo_estimado="1000", custo_realizado="900",
            status="concluida", data_inicio=timezone.localdate(), data_conclusao=timezone.localdate(),
            criado_por=self.usuario,
        )
        categoria = CategoriaFinanceira.objects.create(nome="Venda", aplicacao="receita")
        LancamentoFinanceiro.objects.create(
            tipo="receber", descricao="Venda", valor="2000", valor_liquidado="2000",
            categoria=categoria, propriedade=self.propriedade, safra="2026/2027",
            data_vencimento=timezone.localdate(), data_liquidacao=timezone.localdate(),
            status="liquidado",
        )
        self.maquina = Maquina.objects.create(
            identificacao="REL-1", tipo="trator", propriedade=self.propriedade
        )
        ManutencaoMaquina.objects.create(
            maquina=self.maquina, descricao="Revisão", data_prevista=timezone.localdate()
        )


class DashboardServiceTests(DashboardBase, TestCase):
    def setUp(self): self.dados()

    def test_consolida_indicadores(self):
        dados = dashboard_gerencial()
        self.assertEqual(dados["estrutura"]["propriedades"], 2)
        self.assertEqual(dados["operacoes"]["concluidas"], 1)
        self.assertEqual(dados["financeiro"]["entradas_realizadas"], 2000)
        self.assertEqual(dados["maquinas"]["manutencoes_pendentes"], 1)
        self.assertEqual(len(dados["fluxo_mensal"]), 1)

    def test_filtra_propriedade_e_safra(self):
        dados = dashboard_gerencial(propriedade=self.outra.id, safra="2026/2027")
        self.assertEqual(dados["estrutura"]["talhoes"], 0)
        self.assertEqual(dados["operacoes"]["total"], 0)
        self.assertEqual(dados["financeiro"]["entradas_realizadas"], 0)


class DashboardApiTests(DashboardBase, APITestCase):
    def setUp(self):
        self.dados()
        self.client.force_authenticate(self.usuario)

    def test_exige_autenticacao(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/relatorios/dashboard/").status_code, 401)

    def test_retorna_dashboard_filtrado(self):
        resposta = self.client.get(
            f"/api/relatorios/dashboard/?propriedade={self.propriedade.id}&safra=2026/2027"
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.data["estrutura"]["talhoes"], 1)
        self.assertEqual(resposta.data["operacoes"]["custo_realizado"], 900)

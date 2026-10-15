from datetime import date
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from apps.accounts.models import AcessoUsuario
from apps.transportes.models import Caminhao, LancamentoTransporte, RemuneracaoMotorista
from apps.graos.test_cargas_colhidas import CargaColhidaBase
from apps.graos.cargas_services import registrar_carga_colhida, cancelar_carga_colhida


class RankingFinanceiroTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(username="ranking")
        self.client = APIClient()
        self.client.force_authenticate(self.usuario)
        self.caminhao = Caminhao.objects.create(placa="ABC1D23", veiculo="Volvo", motorista="Atual")
        self.url = "/api/transportes/lancamentos/relatorio/"
        self.filtros = {"data_inicio": "2026-08-01", "data_fim": "2026-08-31"}

    def registrar(self, motorista, tipo, valor, mes=8):
        LancamentoTransporte.objects.create(caminhao=self.caminhao, motorista=motorista, data=date(2026, mes, 10), tipo=tipo, descricao="Frete" if tipo == "receita" else "Combustível", quantidade="1", valor_unitario=valor)

    def test_resultado_e_margem_diferem_de_faturamento(self):
        self.registrar("Alto faturamento", "receita", "1000")
        self.registrar("Alto faturamento", "despesa", "900")
        self.registrar("Melhor resultado", "receita", "600")
        self.registrar("Melhor resultado", "despesa", "100")
        self.registrar("Melhor margem", "receita", "100")
        self.registrar("Sem receita", "despesa", "50")
        RemuneracaoMotorista.objects.create(caminhao=self.caminhao, motorista="Melhor resultado", competencia=date(2026,8,1), salario="100", comissao="50")
        resultado = self.client.get(self.url, self.filtros).data
        self.assertEqual(resultado["ranking_financeiro"][0]["nome"], "Melhor resultado")
        self.assertEqual(resultado["ranking_financeiro"][0]["saldo"], "350.00")
        self.assertEqual(resultado["ranking_eficiencia"][0]["nome"], "Melhor margem")
        self.assertEqual(resultado["ranking_eficiencia"][0]["margem"], "100.00")
        self.assertNotIn("Sem receita", [i["nome"] for i in resultado["ranking_eficiencia"]])
        self.assertTrue(resultado["ranking_financeiro"][0]["remuneracao_cadastrada"])
        self.assertTrue(resultado["ranking_financeiro"][0]["despesas_registradas"])

    def test_filtros_nomes_equivalentes_e_prejuizo(self):
        self.registrar(" Motorista A ", "receita", "100")
        self.registrar("MOTORISTA A", "despesa", "200")
        self.registrar("Fora do período", "receita", "9999", mes=9)
        resposta = self.client.get(self.url, self.filtros).data
        self.assertEqual(len(resposta["ranking_financeiro"]), 1)
        self.assertEqual(resposta["ranking_financeiro"][0]["saldo"], "-100.00")
        self.assertFalse(resposta["ranking_financeiro"][0]["remuneracao_cadastrada"])
        self.assertEqual(resposta["ranking_eficiencia"][0]["margem"], "-100.00")
        self.assertEqual(self.client.get(self.url, {**self.filtros, "caminhao": "99999"}).data["ranking_financeiro"], [])

    def test_exportacao_permissoes_e_vazio(self):
        resposta = self.client.get(self.url, self.filtros).data
        self.assertEqual(resposta["ranking_financeiro"], [])
        self.assertEqual(resposta["ranking_eficiencia"], [])
        csv = self.client.get("/api/transportes/lancamentos/exportar/", self.filtros)
        self.assertEqual(csv.status_code, 200)
        self.assertIn("Ranking financeiro por resultado", csv.content.decode())
        AcessoUsuario.objects.create(usuario=self.usuario, modulos=["financeiro"])
        self.assertEqual(self.client.get(self.url, self.filtros).status_code, 403)


class RankingOperacionalTests(CargaColhidaBase, TestCase):
    def test_volume_medio_historico_e_cancelamento(self):
        self.criar_contexto()
        client = APIClient()
        client.force_authenticate(self.usuario)
        a = registrar_carga_colhida(usuario=self.usuario, **{**self.dados_carga(), "motorista": "Motorista A", "peso_bruto_kg": "1000"})
        registrar_carga_colhida(usuario=self.usuario, **{**self.dados_carga(), "motorista": "Motorista B", "placa": "XYZ9A99", "peso_bruto_kg": "2000"})
        params = {"data_inicio": "2026-08-01", "data_fim": "2026-08-31"}
        url = "/api/transportes/lancamentos/relatorio/"
        resultado = client.get(url, params).data["ranking_operacional"]
        self.assertEqual(resultado[0]["nome"], "Motorista B")
        self.assertEqual(resultado[0]["documentos"], 1)
        self.assertGreater(float(resultado[0]["toneladas_por_documento"]), float(resultado[1]["toneladas_por_documento"]))
        cancelar_carga_colhida(usuario=self.usuario, carga=a)
        self.assertEqual(len(client.get(url, params).data["ranking_operacional"]), 1)
        AcessoUsuario.objects.create(usuario=self.usuario, modulos=["transportes"], permissoes={"transportes": ["consultar"]})
        self.assertEqual(client.get(url, params).data["ranking_operacional"], [])

from datetime import date
from decimal import Decimal
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APITestCase
from apps.accounts.models import AcessoUsuario
from apps.core.painel import construir_painel
from apps.financeiro.models import LancamentoFinanceiro
from apps.propriedades.models import Propriedade
from apps.clima.satelite import extrair_camadas


class RecursosSemCustosTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.admin = get_user_model().objects.create_user("sem-custos-admin", is_staff=True)
        self.user = get_user_model().objects.create_user("sem-custos-consulta")
        self.acesso = AcessoUsuario.objects.create(usuario=self.user, modulos=["insights"], permissoes={"insights": ["consultar"]})
        self.propriedade = Propriedade.objects.create(nome="P1", municipio="Cidade", uf="PR", area_hectares="10")
        self.client.force_authenticate(self.user)

    def lancamento(self, **kwargs):
        dados = dict(tipo="receber", descricao="Receita", valor="100", valor_liquidado="90", status="liquidado", data_vencimento=date(2026,10,10), propriedade=self.propriedade, safra="2026")
        dados.update(kwargs)
        return LancamentoFinanceiro.objects.create(**dados)

    def test_financeiro_realizado_filtra_e_nao_soma_cancelados_ou_nominal(self):
        self.lancamento()
        self.lancamento(tipo="pagar", valor_liquidado="30")
        self.lancamento(status="cancelado", valor_liquidado="999")
        self.lancamento(safra="2027", valor_liquidado="1000")
        self.lancamento(propriedade=None, valor_liquidado="2000")
        self.lancamento(status="pendente", tipo="pagar", valor="20", valor_liquidado=None)
        r = construir_painel(self.admin, self.propriedade.pk,"2026")["resumo"]
        self.assertEqual(Decimal(r["entradas_realizadas"]), Decimal("90"))
        self.assertEqual(Decimal(r["saidas_realizadas"]), Decimal("30"))
        self.assertEqual(Decimal(r["saldo_realizado"]), Decimal("60"))
        self.assertEqual(Decimal(r["saldo_previsto"]), Decimal("-20"))

    def test_liquidacao_sem_valor_identificada_e_financeiro_restrito(self):
        self.lancamento(valor_liquidado=None)
        self.assertEqual(construir_painel(self.admin)["resumo"]["liquidacoes_sem_valor"], 1)
        self.assertNotIn("entradas_realizadas", construir_painel(self.user)["resumo"])

    def test_catalogo_datas_reais_e_camadas_obrigatorias(self):
        xml=b'<WMS><Layer><Name>MODIS_Terra_CorrectedReflectance_TrueColor</Name><Extent name="time" default="2026-10-09"/></Layer><Layer><Name>MODIS_Terra_L3_NDVI_16Day</Name><Extent name="time" default="2026-09-14"/></Layer></WMS>'
        r=extrair_camadas(xml)
        self.assertEqual(r[1]["data"],"2026-09-14")
        self.assertEqual(r[1]["periodo"],"16 dias")
        with self.assertRaises(ValueError): extrair_camadas(b'<WMS/>')
        with self.assertRaises(ValueError): extrair_camadas(xml.replace(b'2026-09-14',b'invalida'))

    @patch("apps.clima.satelite.urllib.request.urlopen", side_effect=OSError)
    def test_nasa_indisponivel_e_restricao_de_modulo(self, rede):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get("/api/clima/satelite/").status_code,503)
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.get("/api/clima/satelite/").status_code,403)

    @patch("apps.ai.chat_local.gerar_resposta", return_value="Dados insuficientes.")
    def test_chat_consulta_permissoes_sem_vazar_financeiro(self, gerar):
        self.lancamento()
        r=self.client.post("/api/ai/conversar/",{"pergunta":"Como estão as finanças?"},format="json")
        self.assertEqual(r.status_code,200,r.data)
        self.assertEqual(r.data["evidencia"]["resumo"],{})
        self.assertNotIn("financeiro", str(gerar.call_args.args[1]))
        self.assertEqual(LancamentoFinanceiro.objects.count(),1)

    @patch("apps.ai.chat_local.gerar_resposta", side_effect=OSError)
    def test_chat_indisponivel_validacao_e_concorrencia(self, gerar):
        self.assertEqual(self.client.post("/api/ai/conversar/",{"pergunta":""},format="json").status_code,400)
        self.assertEqual(self.client.post("/api/ai/conversar/",{"pergunta":"x","propriedade":0},format="json").status_code,400)
        self.assertEqual(self.client.post("/api/ai/conversar/",{"pergunta":"x"},format="json").status_code,503)
        cache.add("chat-local-em-uso",True,65)
        self.assertEqual(self.client.post("/api/ai/conversar/",{"pergunta":"x"},format="json").status_code,429)

    def test_chat_exige_autenticacao_e_consulta(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.post("/api/ai/conversar/",{"pergunta":"x"},format="json").status_code,401)
        self.acesso.modulos=[]; self.acesso.save()
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.post("/api/ai/conversar/",{"pergunta":"x"},format="json").status_code,403)

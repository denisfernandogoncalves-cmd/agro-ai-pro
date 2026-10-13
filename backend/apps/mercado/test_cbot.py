from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APITestCase
from .models import CotacaoCBOT, CotacaoMercado
from .cbot import normalizar_cotacao, atualizar_cbot, SIMBOLOS, NOMES
from .services import ServicoMercadoError


def resposta(simbolo):
    produto = next(p for p,s in SIMBOLOS.items() if s == simbolo)
    return {"chart":{"error":None,"result":[{"meta":{"symbol":simbolo,"exchangeName":"CBT","currency":"USX","shortName":NOMES[produto]+" Futures,Dec-2026","regularMarketPrice":1297.5,"regularMarketTime":int(datetime(2026,1,1,tzinfo=timezone.utc).timestamp())}}]}}


class CotacoesCBOTTests(TestCase):
    def test_converte_centavos_sem_converter_indicador_fred(self):
        r=normalizar_cotacao("soja",resposta("ZS=F"))
        self.assertEqual(r["valor_usd_bushel"],Decimal("12.975000"))
        self.assertEqual(r["valor_centavos_bushel"],Decimal("1297.5"))
        atualizar_cbot(transport=resposta)
        self.assertEqual(CotacaoMercado.objects.count(),0)

    def test_reenvio_e_resposta_antiga_nao_duplicam_nem_regredem_ultima(self):
        atualizar_cbot(transport=resposta);atualizar_cbot(transport=resposta)
        self.assertEqual(CotacaoCBOT.objects.count(),3)
        def velha(s):
            r=resposta(s);r["chart"]["result"][0]["meta"]["regularMarketTime"]-=86400
            return r
        r=atualizar_cbot(transport=velha)
        self.assertTrue(all(i.cotado_em.day==1 for i in r))

    def test_unidade_bolsa_contrato_preco_e_instante_invalidos(self):
        for campo,valor in [("currency","USD"),("exchangeName","NYM"),("symbol","ZW=F"),("shortName","Sem contrato"),("regularMarketPrice","NaN"),("regularMarketPrice",-1),("regularMarketPrice","Infinity"),("regularMarketTime",999999999999)]:
            r=resposta("ZS=F");r["chart"]["result"][0]["meta"][campo]=valor
            with self.subTest(campo=campo,valor=valor),self.assertRaises(ServicoMercadoError): normalizar_cotacao("soja",r)

    def test_nome_de_trigo_truncado_nao_inventa_ano(self):
        from .serializers import CotacaoCBOTSerializer
        r=resposta("ZW=F");r["chart"]["result"][0]["meta"]["shortName"]="Chicago SRW Wheat Futures,Dec-2"
        d=normalizar_cotacao("trigo",r)
        c=CotacaoCBOT(**d)
        self.assertFalse(CotacaoCBOTSerializer(c).data["contrato_completo"])
        self.assertEqual(c.contrato,"Chicago SRW Wheat Futures,Dec-2")

    def test_falha_intermediaria_preserva_todos_os_precos(self):
        atualizar_cbot(transport=resposta)
        antes=list(CotacaoCBOT.objects.values_list("id","valor_usd_bushel"))
        def falhar(s):
            if s=="ZW=F": raise TimeoutError()
            r=resposta(s);r["chart"]["result"][0]["meta"]["regularMarketPrice"]=1400
            return r
        with self.assertRaises(ServicoMercadoError): atualizar_cbot(transport=falhar)
        self.assertEqual(list(CotacaoCBOT.objects.values_list("id","valor_usd_bushel")),antes)


class CotacoesCBOTAPITests(APITestCase):
    def setUp(self):
        self.usuario=get_user_model().objects.create_user(username="cbot",password="senha-segura")
        from rest_framework_simplejwt.tokens import RefreshToken
        self.client.credentials(HTTP_AUTHORIZATION="Bearer "+str(RefreshToken.for_user(self.usuario).access_token))

    def test_consulta_nao_atualiza_provedor(self):
        with patch("apps.mercado.cbot.consultar_provedor") as consultar:
            r=self.client.get("/api/mercado/cbot/")
        self.assertEqual(r.status_code,200);self.assertEqual(r.data,[]);consultar.assert_not_called()
        atualizar_cbot(transport=resposta)
        r=self.client.get("/api/mercado/cbot/")
        self.assertEqual(len(r.data),3)
        self.assertEqual(r.data[0]["unidade"],"US$/bushel")

    def test_sem_autenticacao_e_sem_modulo(self):
        from apps.accounts.models import AcessoUsuario
        AcessoUsuario.objects.update_or_create(usuario=self.usuario,defaults={"modulos":["financeiro"]})
        self.assertEqual(self.client.get("/api/mercado/cbot/").status_code,403)
        self.client.credentials()
        self.assertEqual(self.client.get("/api/mercado/cbot/").status_code,401)

    def test_cotacoes_nao_podem_ser_alteradas_pela_api(self):
        atualizar_cbot(transport=resposta)
        item=CotacaoCBOT.objects.first()
        self.assertEqual(self.client.patch(f"/api/mercado/cbot/{item.pk}/",{"valor_usd_bushel":"0"},format="json").status_code,405)

    def test_consulta_sem_permissao_de_cadastrar_nao_atualiza(self):
        from apps.accounts.models import AcessoUsuario
        AcessoUsuario.objects.update_or_create(usuario=self.usuario,defaults={"modulos":["mercado"],"permissoes":{"mercado":["consultar"]}})
        with patch("apps.mercado.cbot.atualizar_cbot") as atualizar:
            r=self.client.post("/api/mercado/cbot/atualizar/",{},format="json")
        self.assertEqual(r.status_code,403);atualizar.assert_not_called()

    def test_falha_na_atualizacao_retorna_503_preservando_consulta(self):
        atualizar_cbot(transport=resposta)
        with patch("apps.mercado.cbot.atualizar_cbot",side_effect=ServicoMercadoError("Provedor indisponível")):
            r=self.client.post("/api/mercado/cbot/atualizar/",{},format="json")
        self.assertEqual(r.status_code,503)
        self.assertEqual(len(self.client.get("/api/mercado/cbot/").data),3)

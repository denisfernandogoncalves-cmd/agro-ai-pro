import json
from unittest.mock import patch
from django.test import SimpleTestCase, override_settings
from django.core.cache import cache
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from .investing import REFERENCIAS, normalizar, consultar_referencia


def pagina(produto="soja", valor=1297.5):
    caminho, identidade, codigo, _ = REFERENCIAS[produto]
    instrumento={"base":{"id":identidade,"path":"/"+caminho,"type":"currency" if produto=="dolar" else "commodity","isCfd":produto!="dolar","isOpen":True},
       "name":{"shortName":codigo,"base_symbol":codigo},
       "price":{"last":valor,"currency":"BRL" if produto=="dolar" else "USD","lastUpdateTime":"1767225600000","isDelayed":False},
       "commodityData":{"unit":"_instr_unit_bushel"}}
    return '<script id="__NEXT_DATA__" type="application/json">'+json.dumps({"props":{"pageProps":{"state":{"currencyStore" if produto=="dolar" else "commodityStore":{"instrument":instrumento}}}}})+'</script>'


@override_settings(CACHES={"default":{"BACKEND":"django.core.cache.backends.locmem.LocMemCache","LOCATION":"investing-tests"}})
class InvestingTests(SimpleTestCase):
    def setUp(self): cache.clear()
    def tearDown(self): cache.clear()

    def test_conversao_e_dolar_sem_dividir_por_cem(self):
        self.assertEqual(normalizar("soja",pagina())["valor"],"12.975")
        dolar=normalizar("dolar",pagina("dolar",5.0127))
        self.assertEqual(dolar["valor"],"5.0127");self.assertEqual(dolar["unidade"],"R$/US$")
        self.assertFalse(dolar["derivado"])
        self.assertTrue(normalizar("soja",pagina())["derivado"])

    def test_identidade_unidade_e_preco_invalidos(self):
        casos=[pagina().replace('8916','8918'),pagina().replace('bushel','ton'),pagina().replace('USD','BRL'),pagina(valor=-1),pagina(valor=float('nan')),pagina().replace('1767225600000','999999999999999999'),'<html>bloqueado</html>']
        for html in casos:
            with self.subTest(html=html[:40]):
                with self.assertRaises(ValueError):normalizar("soja",html)

    def test_cache_limita_consultas_e_preserva_horario_apos_falha(self):
        with patch("apps.mercado.investing.consultar_pagina") as transporte:
            transporte.return_value=pagina()
            # Transport explícito evita argumento padrão capturado no import.
            primeiro=consultar_referencia("soja",transporte)
            self.assertEqual(consultar_referencia("soja",transporte),primeiro)
            self.assertEqual(transporte.call_count,1)
            cache.delete("investing:v1:soja:aguardar")
            transporte.side_effect=TimeoutError()
            antigo=consultar_referencia("soja",transporte)
            self.assertEqual(antigo["valor"],primeiro["valor"])
            self.assertEqual(antigo["cotado_em"],primeiro["cotado_em"])
            self.assertTrue(antigo["erro"])
            consultar_referencia("soja",transporte)
            self.assertEqual(transporte.call_count,2)

    def test_falha_sem_preco_nao_inventa_valor(self):
        with patch("apps.mercado.investing.consultar_pagina",side_effect=OSError()) as transporte:
            self.assertNotIn("valor",consultar_referencia("dolar",transporte))

    def test_resposta_antiga_nao_regride_cotacao(self):
        primeiro=consultar_referencia("soja",lambda _:pagina())
        cache.delete("investing:v1:soja:aguardar")
        antigo=consultar_referencia("soja",lambda _:pagina(valor=1000).replace('1767225600000','1735689600000'))
        self.assertEqual(antigo["valor"],primeiro["valor"])
        self.assertTrue(antigo["erro"])


class InvestingAPITests(APITestCase):
    def setUp(self):
        self.usuario=get_user_model().objects.create_user(username="investing-teste",password="senha-de-teste")
        self.client.credentials(HTTP_AUTHORIZATION="Bearer "+str(RefreshToken.for_user(self.usuario).access_token))

    def test_consulta_autorizada_sem_cadastrar(self):
        from apps.accounts.models import AcessoUsuario
        AcessoUsuario.objects.update_or_create(usuario=self.usuario,defaults={"modulos":["mercado"],"permissoes":{"mercado":["consultar"]}})
        with patch("apps.mercado.investing.consultar_referencias",return_value={"cotacoes":[],"intervalo_segundos":60}):
            self.assertEqual(self.client.get("/api/mercado/investing/").status_code,200)
        self.assertEqual(self.client.post("/api/mercado/investing/",{}).status_code,403)
        AcessoUsuario.objects.update_or_create(usuario=self.usuario,defaults={"modulos":["mercado"],"permissoes":{"mercado":["consultar","cadastrar"]}})
        self.assertEqual(self.client.post("/api/mercado/investing/",{}).status_code,405)

    def test_sem_modulo_ou_sessao_nao_consulta_provedor(self):
        from apps.accounts.models import AcessoUsuario
        AcessoUsuario.objects.update_or_create(usuario=self.usuario,defaults={"modulos":["financeiro"]})
        with patch("apps.mercado.investing.consultar_referencias") as transporte:
            self.assertEqual(self.client.get("/api/mercado/investing/").status_code,403)
            self.client.credentials()
            self.assertEqual(self.client.get("/api/mercado/investing/").status_code,401)
            transporte.assert_not_called()

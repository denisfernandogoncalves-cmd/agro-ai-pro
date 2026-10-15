from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import SimpleTestCase, override_settings
from rest_framework.test import APIRequestFactory, force_authenticate

from .referencias import consultar_chicago
from .test_cbot import resposta
from .views import ReferenciasMercadoViewSet


@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "referencias-tests"}})
class ReferenciasTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_contrato_unidade_fonte_e_cache(self):
        transport = Mock(side_effect=resposta)
        for produto in ("soja", "milho", "trigo"):
            dado = consultar_chicago(produto, transport)
            self.assertEqual(dado["valor"], "12.975000")
            self.assertEqual(dado["unidade"], "US$/bushel")
            self.assertEqual(dado["fonte"], "Yahoo Finance / CBOT")
            self.assertIn("Dec-2026", dado["contrato"])
            self.assertTrue(dado["atraso_provedor"])
            self.assertNotIn("mercado_aberto", dado)
            self.assertEqual(consultar_chicago(produto, transport), dado)
        self.assertEqual(transport.call_count, 3)

    def test_falha_preserva_preco_horario_e_limita_novas_tentativas(self):
        anterior = consultar_chicago("soja", resposta)
        cache.delete("yahoo:cbot:v1:soja:aguardar")
        falha = Mock(side_effect=TimeoutError)
        dado = consultar_chicago("soja", falha)
        self.assertEqual(dado["valor"], anterior["valor"])
        self.assertEqual(dado["cotado_em"], anterior["cotado_em"])
        self.assertTrue(dado["erro"])
        consultar_chicago("soja", falha)
        falha.assert_called_once()

    def test_falha_inicial_nao_inventa_preco(self):
        self.assertNotIn("valor", consultar_chicago("trigo", Mock(side_effect=OSError)))

    def test_resposta_antiga_e_unidade_invalida_preservam_preco(self):
        anterior = consultar_chicago("soja", resposta)
        for campo, valor in (("regularMarketTime", 1704067200), ("currency", "USD")):
            cache.delete("yahoo:cbot:v1:soja:aguardar")
            dados = resposta("ZS=F")
            dados["chart"]["result"][0]["meta"][campo] = valor
            atual = consultar_chicago("soja", lambda _: dados)
            self.assertEqual(atual["valor"], anterior["valor"])
            self.assertEqual(atual["cotado_em"], anterior["cotado_em"])
            self.assertTrue(atual["erro"])

    def test_endpoint_autenticado_e_somente_leitura(self):
        view = ReferenciasMercadoViewSet.as_view({"get": "list"})
        factory = APIRequestFactory()
        with patch("apps.mercado.referencias.consultar_referencias", return_value={"cotacoes": []}) as provedor:
            self.assertEqual(view(factory.get("/")).status_code, 401)
            provedor.assert_not_called()
            request = factory.get("/")
            force_authenticate(request, user=Mock(is_authenticated=True))
            self.assertEqual(view(request).status_code, 200)
            request = factory.post("/")
            force_authenticate(request, user=Mock(is_authenticated=True))
            self.assertEqual(view(request).status_code, 405)

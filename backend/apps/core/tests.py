from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken


class ProtecaoGlobalApiTests(APITestCase):
    PRIVATE_READ_URLS = (
        "/api/ai/insights/",
        "/api/clima/previsoes/",
        "/api/estoque/produtos/",
        "/api/financeiro/categorias/",
        "/api/maquinas/maquinas/",
        "/api/mercado/cotacoes/",
        "/api/producao/operacoes/",
        "/api/propriedades/",
        "/api/relatorios/dashboard/",
        "/api/talhoes/talhoes/",
    )

    def test_apis_privadas_rejeitam_leitura_anonima(self):
        for url in self.PRIVATE_READ_URLS:
            with self.subTest(url=url):
                self.assertEqual(
                    self.client.get(url).status_code,
                    status.HTTP_401_UNAUTHORIZED,
                )

    def test_api_privada_rejeita_token_invalido_e_escrita_anonima(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer token-invalido")
        self.assertEqual(
            self.client.get("/api/propriedades/").status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.client.credentials()
        self.assertEqual(
            self.client.post(
                "/api/propriedades/",
                {},
                format="json",
            ).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_api_privada_nao_permite_cache_e_varia_por_autorizacao(self):
        usuario = get_user_model().objects.create_user(username="cache")
        access = str(AccessToken.for_user(usuario))
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        resposta = self.client.get("/api/propriedades/")

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertIn("no-store", resposta["Cache-Control"])
        self.assertIn("private", resposta["Cache-Control"])
        self.assertIn("Authorization", resposta["Vary"])

    def test_endpoints_publicos_nao_recebem_cache_privado(self):
        for url in ("/api/health/", "/api/schema.json"):
            with self.subTest(url=url):
                resposta = self.client.get(
                    url,
                    HTTP_ACCEPT="application/json",
                )
                self.assertEqual(resposta.status_code, status.HTTP_200_OK)
                self.assertNotIn(
                    "private",
                    resposta.get("Cache-Control", ""),
                )

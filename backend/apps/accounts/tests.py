from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.db import close_old_connections, connection
from django.test import TransactionTestCase
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken


def adulterar_assinatura(token):
    cabecalho, payload, assinatura = token.split(".")
    primeiro = "A" if assinatura[0] != "A" else "B"
    return ".".join((cabecalho, payload, primeiro + assinatura[1:]))


class AutenticacaoJWTTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(
            username="gestor",
            password="senha-segura",
        )
        cls.usuario_inativo = get_user_model().objects.create_user(
            username="inativo",
            password="senha-segura",
            is_active=False,
        )

    def login(self):
        return self.client.post(
            "/api/auth/token/",
            {"username": "gestor", "password": "senha-segura"},
            format="json",
        )

    def assert_no_store_private(self, resposta):
        cache_control = resposta["Cache-Control"]
        self.assertIn("no-store", cache_control)
        self.assertIn("private", cache_control)
        self.assertIn("Authorization", resposta["Vary"])

    def test_login_valido_emite_tokens_e_nao_permite_cache(self):
        resposta = self.login()

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertIn("access", resposta.data)
        self.assertIn("refresh", resposta.data)
        self.assert_no_store_private(resposta)

    def test_login_rejeita_credenciais_invalidas(self):
        resposta = self.client.post(
            "/api/auth/token/",
            {"username": "inexistente", "password": "incorreta"},
            format="json",
        )

        self.assertEqual(resposta.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assert_no_store_private(resposta)

    def test_login_rejeita_usuario_inativo(self):
        resposta = self.client.post(
            "/api/auth/token/",
            {"username": "inativo", "password": "senha-segura"},
            format="json",
        )

        self.assertEqual(resposta.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_rotaciona_e_bloqueia_o_anterior(self):
        refresh_anterior = self.login().data["refresh"]

        resposta = self.client.post(
            "/api/auth/token/refresh/",
            {"refresh": refresh_anterior},
            format="json",
        )

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertIn("access", resposta.data)
        self.assertIn("refresh", resposta.data)
        self.assertNotEqual(resposta.data["refresh"], refresh_anterior)
        self.assert_no_store_private(resposta)
        self.assertEqual(
            self.client.post(
                "/api/auth/token/refresh/",
                {"refresh": refresh_anterior},
                format="json",
            ).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertEqual(
            self.client.post(
                "/api/auth/token/refresh/",
                {"refresh": resposta.data["refresh"]},
                format="json",
            ).status_code,
            status.HTTP_200_OK,
        )

    def test_refresh_rejeita_expirado_malformado_assinatura_e_tipo(self):
        expirado = RefreshToken.for_user(self.usuario)
        expirado.set_exp(lifetime=timedelta(seconds=-1))
        entradas = (
            str(expirado),
            "token-malformado",
            adulterar_assinatura(str(RefreshToken.for_user(self.usuario))),
            str(AccessToken.for_user(self.usuario)),
        )

        for refresh in entradas:
            with self.subTest(refresh=refresh[:12]):
                resposta = self.client.post(
                    "/api/auth/token/refresh/",
                    {"refresh": refresh},
                    format="json",
                )
                self.assertEqual(
                    resposta.status_code,
                    status.HTTP_401_UNAUTHORIZED,
                )

    def test_refresh_rejeita_revogado_e_reutilizado(self):
        refresh = RefreshToken.for_user(self.usuario)
        refresh.blacklist()

        for _ in range(2):
            resposta = self.client.post(
                "/api/auth/token/refresh/",
                {"refresh": str(refresh)},
                format="json",
            )
            self.assertEqual(resposta.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_rejeita_usuario_que_foi_inativado(self):
        refresh = RefreshToken.for_user(self.usuario)
        self.usuario.is_active = False
        self.usuario.save(update_fields=["is_active"])

        resposta = self.client.post(
            "/api/auth/token/refresh/",
            {"refresh": str(refresh)},
            format="json",
        )

        self.assertEqual(resposta.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_valido_repetido_e_refresh_posterior(self):
        refresh = self.login().data["refresh"]

        primeira = self.client.post(
            "/api/auth/logout/",
            {"refresh": refresh},
            format="json",
        )
        segunda = self.client.post(
            "/api/auth/logout/",
            {"refresh": refresh},
            format="json",
        )

        self.assertEqual(primeira.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(segunda.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(primeira.content, b"")
        self.assert_no_store_private(primeira)
        self.assertEqual(
            self.client.post(
                "/api/auth/token/refresh/",
                {"refresh": refresh},
                format="json",
            ).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_logout_nao_exige_access_valido(self):
        refresh = self.login().data["refresh"]
        resposta = self.client.post(
            "/api/auth/logout/",
            {"refresh": refresh},
            format="json",
            HTTP_AUTHORIZATION="Bearer access-invalido",
        )

        self.assertEqual(resposta.status_code, status.HTTP_204_NO_CONTENT)

    def test_logout_expirado_valido_e_idempotente(self):
        refresh = RefreshToken.for_user(self.usuario)
        refresh.set_exp(lifetime=timedelta(seconds=-1))

        for _ in range(2):
            resposta = self.client.post(
                "/api/auth/logout/",
                {"refresh": str(refresh)},
                format="json",
            )
            self.assertEqual(resposta.status_code, status.HTTP_204_NO_CONTENT)

    def test_logout_rejeita_entradas_invalidas_sem_erro_interno(self):
        access_expirado = AccessToken.for_user(self.usuario)
        access_expirado.set_exp(lifetime=timedelta(seconds=-1))
        entradas = (
            {},
            {"refresh": ""},
            {"refresh": "token-malformado"},
            {
                "refresh": adulterar_assinatura(
                    str(RefreshToken.for_user(self.usuario))
                )
            },
            {"refresh": str(AccessToken.for_user(self.usuario))},
            {"refresh": str(access_expirado)},
        )

        for corpo in entradas:
            with self.subTest(corpo=list(corpo)):
                resposta = self.client.post(
                    "/api/auth/logout/",
                    corpo,
                    format="json",
                )
                self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
                self.assert_no_store_private(resposta)

    def test_logout_nao_registra_token_completo(self):
        refresh = self.login().data["refresh"]

        with self.assertLogs("apps.accounts.services", level="INFO") as logs:
            resposta = self.client.post(
                "/api/auth/logout/",
                {"refresh": refresh},
                format="json",
            )

        self.assertEqual(resposta.status_code, status.HTTP_204_NO_CONTENT)
        self.assertNotIn(refresh, "\n".join(logs.output))

    def test_openapi_documenta_logout_e_rotacao(self):
        resposta = self.client.get(
            "/api/schema.json",
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        documento = resposta.json()
        self.assertEqual(documento["basePath"], "/api")
        self.assertIn("/auth/logout/", documento["paths"])
        logout = documento["paths"]["/auth/logout/"]["post"]
        self.assertIn("post", documento["paths"]["/auth/logout/"])
        self.assertEqual(
            logout["responses"]["204"]["headers"]["Cache-Control"]["default"],
            "no-store, private",
        )
        self.assertIn("example", documento["definitions"]["Logout"])
        self.assertIn("/auth/token/refresh/", documento["paths"])
        self.assertIn(
            "200",
            documento["paths"]["/auth/token/"]["post"]["responses"],
        )


@skipUnless(
    connection.vendor == "postgresql",
    "Concorrência transacional requer PostgreSQL.",
)
class ConcorrenciaJWTPostgreSQLTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.usuario = get_user_model().objects.create_user(
            username="concorrencia",
            password="senha-segura",
        )

    def executar_post(self, url, refresh):
        close_old_connections()
        try:
            return APIClient().post(
                url,
                {"refresh": refresh},
                format="json",
            ).status_code
        finally:
            close_old_connections()

    def test_logout_simultaneo_e_controlado(self):
        refresh = str(RefreshToken.for_user(self.usuario))
        with ThreadPoolExecutor(max_workers=2) as executor:
            resultados = list(
                executor.map(
                    lambda _: self.executar_post(
                        "/api/auth/logout/",
                        refresh,
                    ),
                    range(2),
                )
            )

        self.assertEqual(resultados, [204, 204])

    def test_refresh_simultaneo_nao_reutiliza_token_antigo(self):
        refresh = str(RefreshToken.for_user(self.usuario))
        with ThreadPoolExecutor(max_workers=2) as executor:
            resultados = list(
                executor.map(
                    lambda _: self.executar_post(
                        "/api/auth/token/refresh/",
                        refresh,
                    ),
                    range(2),
                )
            )

        self.assertTrue(set(resultados).issubset({200, 401}))
        self.assertIn(200, resultados)
        self.assertEqual(
            self.executar_post("/api/auth/token/refresh/", refresh),
            401,
        )

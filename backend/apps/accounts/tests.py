from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase


class AutenticacaoJWTTests(APITestCase):
    def test_emite_tokens_para_usuario_ativo(self):
        get_user_model().objects.create_user(
            username="gestor",
            password="senha-segura",
        )

        resposta = self.client.post(
            "/api/auth/token/",
            {"username": "gestor", "password": "senha-segura"},
            format="json",
        )

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertIn("access", resposta.data)
        self.assertIn("refresh", resposta.data)

    def test_rejeita_credenciais_invalidas(self):
        resposta = self.client.post(
            "/api/auth/token/",
            {"username": "inexistente", "password": "incorreta"},
            format="json",
        )

        self.assertEqual(resposta.status_code, status.HTTP_401_UNAUTHORIZED)

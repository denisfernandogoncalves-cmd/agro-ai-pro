from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from .models import ArmazemGraos


class AtivarArmazemTests(APITestCase):
    def test_reativa_armazem_sem_alterar_nome_capacidade_ou_criar_outro(self):
        usuario = get_user_model().objects.create_user("ativacao-armazem")
        self.client.force_authenticate(usuario)
        armazem = ArmazemGraos.objects.create(nome="Silo de teste", capacidade_kg="15000000", ativo=False)
        resposta = self.client.patch(f"/api/graos/armazens/{armazem.pk}/", {"ativo": True}, format="json")
        self.assertEqual(resposta.status_code, 200, resposta.data)
        armazem.refresh_from_db()
        self.assertTrue(armazem.ativo)
        self.assertEqual(armazem.nome, "Silo de teste")
        self.assertEqual(armazem.capacidade_kg, 15000000)
        self.assertEqual(ArmazemGraos.objects.count(), 1)

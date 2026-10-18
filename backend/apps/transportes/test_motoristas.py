from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework.exceptions import PermissionDenied
from apps.accounts.access import verificar_acesso
from apps.accounts.models import AcessoUsuario
from .models import Motorista, Caminhao


class MotoristasTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="cadastro-motoristas", is_staff=True)
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.url = "/api/transportes/motoristas/"

    def test_cadastro_apelido_edicao_e_inativacao(self):
        r = self.client.post(self.url, {"nome": "João da Silva", "apelido": "Juca"}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data["apelido"], "Juca")
        self.assertEqual(Caminhao.objects.count(), 0)
        detalhe = f"{self.url}{r.data['id']}/"
        versao = r.data["versao_correcao"]
        atualizado = self.client.patch(detalhe, {"apelido": "João", "ativo": False, "versao_correcao_original": versao}, format="json")
        self.assertEqual(atualizado.status_code, 200, atualizado.data)
        self.assertFalse(atualizado.data["ativo"])
        self.assertEqual(atualizado.data["apelido"], "João")
        self.assertEqual(self.client.patch(detalhe, {"apelido": "Antigo", "versao_correcao_original": versao}, format="json").status_code, 409)
        self.assertEqual(self.client.delete(detalhe).status_code, 400)
        self.assertEqual(Motorista.objects.get().nome, "João da Silva")

    def test_nome_obrigatorio_unico_apelido_opcional(self):
        self.assertEqual(self.client.post(self.url, {"nome": "   "}, format="json").status_code, 400)
        self.assertEqual(self.client.post(self.url, {"nome": "Pedro"}, format="json").status_code, 201)
        self.assertEqual(self.client.post(self.url, {"nome": "Pedro"}, format="json").status_code, 400)
        self.assertEqual(Motorista.objects.get().apelido, "")

    def test_consulta_cargas_nao_libera_cadastro_transportes(self):
        user = get_user_model().objects.create_user(username="somente-cargas")
        AcessoUsuario.objects.create(usuario=user, modulos=["cargas"], permissoes={"cargas": ["consultar"]})
        verificar_acesso(user, self.url, "GET")
        verificar_acesso(user, "/api/transportes/caminhoes/", "GET")
        with self.assertRaises(PermissionDenied):
            verificar_acesso(user, self.url, "POST")
        self.client.force_authenticate(user)
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.assertEqual(self.client.post(self.url, {"nome": "Não autorizado"}, format="json").status_code, 403)

    def test_autenticacao_obrigatoria(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(self.url).status_code, 401)

    def test_excluir_preserva_cadastro_e_reativacao_com_versao(self):
        r = self.client.post(self.url, {"nome":"Motorista teste", "apelido":"Teste"}, format="json")
        detalhe = f"{self.url}{r.data['id']}/"
        caminhao = Caminhao.objects.create(placa="ABC1D23", veiculo="Teste", motorista="Motorista teste")
        dados = {"versao_correcao_original":r.data["versao_correcao"]}
        excluido = self.client.delete(detalhe, dados, format="json")
        self.assertEqual(excluido.status_code, 200, excluido.data)
        self.assertFalse(excluido.data["ativo"])
        self.assertEqual(Motorista.objects.count(), 1)
        caminhao.refresh_from_db()
        self.assertEqual(caminhao.motorista, "Motorista teste")
        self.assertEqual(self.client.delete(detalhe, dados, format="json").status_code, 409)
        reativado = self.client.patch(detalhe, {"ativo":True, "versao_correcao_original":excluido.data["versao_correcao"]}, format="json")
        self.assertEqual(reativado.status_code, 200, reativado.data)
        self.assertTrue(reativado.data["ativo"])

    def test_permissao_editar_nao_autoriza_excluir(self):
        motorista = Motorista.objects.create(nome="Motorista protegido")
        user = get_user_model().objects.create_user(username="editar-sem-excluir")
        AcessoUsuario.objects.create(usuario=user, modulos=["transportes"], permissoes={"transportes":["consultar", "editar"]})
        self.client.force_authenticate(user)
        r = self.client.delete(f"{self.url}{motorista.pk}/", {}, format="json")
        self.assertEqual(r.status_code, 403)
        motorista.refresh_from_db()
        self.assertTrue(motorista.ativo)

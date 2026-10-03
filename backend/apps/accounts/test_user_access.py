from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from .access import MODULOS
from .models import AcessoUsuario


class UserManagementTests(APITestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user("gestor", is_staff=True)
        self.user = get_user_model().objects.create_user("operador", password="Campo!Seguro2026")
        self.client.force_authenticate(self.admin)
        self.url = f"/api/auth/users/{self.user.pk}/"

    def test_edit_without_password_preserves_hash_and_privileges(self):
        senha = self.user.password
        response = self.client.patch(self.url, {"first_name": "Maria", "email": "maria@example.com", "is_staff": True, "is_superuser": True, "modulos": ["cargas", "cargas"]}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.user.refresh_from_db()
        self.assertEqual(self.user.password, senha)
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)
        self.assertEqual(self.user.first_name, "Maria")
        self.assertEqual(response.data["modulos"], ["cargas"])
        self.assertNotIn("password", response.data)

    def test_explicit_password_update_and_validation(self):
        for dados in [{"password": "12345678", "password_confirmation": "12345678"}, {"password": "Campo!SeguroABC"}, {"password_confirmation": "abc"}]:
            self.assertEqual(self.client.patch(self.url, dados, format="json").status_code, 400)
        self.assertEqual(self.client.patch(self.url, {"password": "Campo!SeguroABC", "password_confirmation": "Campo!SeguroABC"}, format="json").status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Campo!SeguroABC"))

    def test_unknown_module_is_rejected_atomically(self):
        response = self.client.patch(self.url, {"first_name": "Alterado", "modulos": ["usuarios"]}, format="json")
        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "")

    def test_empty_permissions_and_legacy_compatibility(self):
        self.assertEqual(self.client.get(self.url).data["modulos"], list(MODULOS))
        self.assertEqual(self.client.patch(self.url, {"modulos": []}, format="json").data["modulos"], [])

    def test_only_admin_can_edit_delete_or_read_user_detail(self):
        for user, expected in [(None, 401), (self.user, 403)]:
            self.client.force_authenticate(user)
            for method in [self.client.get, self.client.patch, self.client.delete]:
                self.assertEqual(method(self.url).status_code, expected)

    def test_cannot_deactivate_or_delete_self(self):
        url = f"/api/auth/users/{self.admin.pk}/"
        self.assertEqual(self.client.delete(url).status_code, 400)
        self.assertEqual(self.client.patch(url, {"is_active": False}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(url, {"modulos": []}, format="json").status_code, 400)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_staff_cannot_edit_or_delete_superuser(self):
        root = get_user_model().objects.create_superuser("root", "root@example.com", "Campo!Seguro2026")
        url = f"/api/auth/users/{root.pk}/"
        self.assertEqual(self.client.patch(url, {"email": "other@example.com"}, format="json").status_code, 400)
        self.assertEqual(self.client.delete(url).status_code, 400)

    def test_delete_preserves_user_record_and_blocks_existing_tokens(self):
        token = str(AccessToken.for_user(self.user))
        refresh = str(RefreshToken.for_user(self.user))
        self.assertEqual(self.client.delete(self.url).status_code, 204)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertIsNotNone(self.user.acesso_modulos.excluido_em)
        self.assertNotIn(self.user.pk, [item["id"] for item in self.client.get("/api/auth/users/").data])
        self.assertEqual(self.client.patch(self.url, {"is_active": True}, format="json").status_code, 404)
        self.client.force_authenticate(None)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 401)
        self.client.credentials()
        self.assertEqual(self.client.post("/api/auth/token/", {"username": "operador", "password": "Campo!Seguro2026"}).status_code, 401)
        self.assertEqual(self.client.post("/api/auth/token/refresh/", {"refresh": refresh}).status_code, 401)

    def test_create_with_selected_access_and_status(self):
        response = self.client.post("/api/auth/users/", {"username": "novo", "password": "Campo!SeguroABC", "password_confirmation": "Campo!SeguroABC", "modulos": ["mercado"], "is_active": False}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["modulos"], ["mercado"])
        self.assertFalse(response.data["is_active"])

    def test_request_authenticated_before_admin_revocation_cannot_mutate(self):
        # Simula uma autenticação concluída antes de o administrador ser desativado.
        get_user_model().objects.filter(pk=self.admin.pk).update(is_active=False)
        self.assertTrue(self.admin.is_active)
        payload = {"username": "negado", "password": "Campo!SeguroABC", "password_confirmation": "Campo!SeguroABC"}
        self.assertEqual(self.client.post("/api/auth/users/", payload, format="json").status_code, 403)
        self.assertEqual(self.client.patch(self.url, {"first_name": "negado"}, format="json").status_code, 403)
        self.assertEqual(self.client.delete(self.url).status_code, 403)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "")
        self.assertTrue(self.user.is_active)
        self.assertFalse(get_user_model().objects.filter(username="negado").exists())


class ModuleAccessTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("operador")
        self.acesso = AcessoUsuario.objects.create(usuario=self.user, modulos=["mercado"])
        self.token = str(AccessToken.for_user(self.user))
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

    def permitir(self, *modulos):
        self.acesso.modulos = list(modulos)
        self.acesso.save()

    def test_allowed_module_and_forbidden_direct_api(self):
        self.assertEqual(self.client.get("/api/mercado/cotacoes/").status_code, 200)
        self.assertEqual(self.client.get("/api/financeiro/lancamentos/").status_code, 403)
        self.assertEqual(self.client.post("/api/financeiro/lancamentos/", {}, format="json").status_code, 403)
        self.assertEqual(self.client.get("/api/auth/users/").status_code, 403)

    def test_existing_token_obeys_changes_immediately(self):
        self.permitir("financeiro")
        self.assertEqual(self.client.get("/api/mercado/cotacoes/").status_code, 403)
        self.assertEqual(self.client.get("/api/financeiro/lancamentos/").status_code, 200)
        self.assertEqual(self.client.get("/api/auth/me/").data["modulos"], ["financeiro"])

    def test_no_modules_blocks_business_endpoints_but_not_me(self):
        self.permitir()
        for path in ["/api/propriedades/", "/api/talhoes/talhoes/", "/api/estoque/compras/", "/api/comercial/vendas/", "/api/graos/saldos/", "/api/relatorios/operacionais/", "/api/importacoes/lotes/"]:
            self.assertEqual(self.client.get(path).status_code, 403, path)
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 200)

    def test_dependencies_read_only_for_loads(self):
        self.permitir("cargas")
        for path in ["/api/propriedades/", "/api/talhoes/talhoes/", "/api/talhoes/grupos-colheita/", "/api/cadpros/", "/api/graos/armazens/", "/api/graos/cargas-colhidas/"]:
            self.assertEqual(self.client.get(path).status_code, 200, path)
        for path in ["/api/propriedades/", "/api/talhoes/talhoes/", "/api/graos/armazens/", "/api/cadpros/"]:
            self.assertEqual(self.client.post(path, {}, format="json").status_code, 403, path)
        self.assertEqual(self.client.post("/api/graos/cargas-colhidas/", {}, format="json").status_code, 400)

    def test_transfer_access_does_not_grant_other_stock_writes(self):
        self.permitir("transferencias")
        self.assertEqual(self.client.get("/api/graos/saldos/painel/").status_code, 200)
        self.assertEqual(self.client.post("/api/graos/saldos/transferir/", {}, format="json").status_code, 400)
        self.assertEqual(self.client.post("/api/graos/saldos/creditar-producao/", {}, format="json").status_code, 403)
        self.assertEqual(self.client.post("/api/graos/saldos/registrar-ajuste/", {}, format="json").status_code, 403)

    def test_invoice_permissions_separate_from_stock(self):
        self.permitir("faturamento-insumos")
        self.assertEqual(self.client.get("/api/estoque/faturamentos/").status_code, 200)
        self.assertEqual(self.client.get("/api/estoque/produtos/").status_code, 200)
        self.assertEqual(self.client.get("/api/financeiro/parceiros/").status_code, 200)
        self.assertEqual(self.client.get("/api/estoque/compras/").status_code, 403)
        self.assertEqual(self.client.post("/api/estoque/produtos/", {}, format="json").status_code, 403)
        self.permitir("estoque")
        self.assertEqual(self.client.get("/api/estoque/faturamentos/").status_code, 403)

    def test_admin_and_existing_user_preserve_access(self):
        self.acesso.delete()
        self.assertEqual(self.client.get("/api/financeiro/lancamentos/").status_code, 200)
        self.user.is_staff = True
        self.user.save()
        AcessoUsuario.objects.create(usuario=self.user, modulos=[])
        self.assertEqual(self.client.get("/api/auth/users/").status_code, 200)
        self.assertEqual(self.client.get("/api/auth/me/").data["modulos"], list(MODULOS))

    def test_each_module_can_load_its_main_resource(self):
        resources = {
            "propriedades": "/api/propriedades/", "talhoes": "/api/talhoes/talhoes/",
            "cadastros-agricolas": "/api/graos/armazens/", "cargas": "/api/graos/cargas-colhidas/",
            "producao-saldos": "/api/graos/saldos/painel/", "transferencias": "/api/graos/saldos/painel/",
            "vendas": "/api/comercial/vendas/", "clima": "/api/clima/previsoes/",
            "mercado": "/api/mercado/cotacoes/", "financeiro": "/api/financeiro/lancamentos/",
            "estoque": "/api/estoque/compras/", "operacoes": "/api/producao/operacoes/",
            "maquinas": "/api/maquinas/maquinas/", "faturamento-insumos": "/api/estoque/faturamentos/",
            "relatorios": "/api/relatorios/operacionais/", "importacoes": "/api/importacoes/lotes/",
            "insights": "/api/ai/insights/",
        }
        for module, path in resources.items():
            with self.subTest(module=module):
                self.permitir(module)
                self.assertEqual(self.client.get(path).status_code, 200)
                self.assertEqual(self.client.get("/api/auth/users/").status_code, 403)

    def test_production_permission_does_not_allow_legacy_transfer_route(self):
        self.permitir("producao-saldos")
        self.assertEqual(self.client.post("/api/graos/lotes/1/transferir/", {}, format="json").status_code, 403)

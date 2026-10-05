from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from apps.accounts.models import AcessoUsuario


class FavoritosConsultasTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("favoritos-consulta")
        self.outro = get_user_model().objects.create_user("outro-consulta")
        self.acesso = AcessoUsuario.objects.create(usuario=self.user, modulos=["cargas", "transferencias"], permissoes={"cargas":["consultar"], "transferencias":["consultar"]})
        AcessoUsuario.objects.create(usuario=self.outro, modulos=["transferencias"], permissoes={"transferencias":["consultar"]})
        self.client.force_authenticate(self.user)

    def test_filtros_completos_legado_e_isolamento(self):
        filtros = {"search":"#52", "mostrarHistorico":True, "cultura":"Soja", "safra":"2026/2027", "propriedade":"2"}
        for contexto in ("cargas", "transferencias"):
            resposta = self.client.post("/api/core/favoritos/", {"contexto":contexto,"nome":"Consulta completa","filtros":filtros}, format="json")
            self.assertEqual(resposta.status_code, 201, resposta.data)
            self.assertEqual(resposta.data["filtros"], filtros)
        pk = resposta.data["id"]
        self.assertEqual(self.client.post("/api/core/favoritos/", {"contexto":"cargas","nome":"Legado","filtros":{"search":"milho"}}, format="json").status_code, 201)
        self.client.force_authenticate(self.outro)
        self.assertEqual(self.client.get("/api/core/favoritos/?contexto=transferencias").data, [])
        self.assertEqual(self.client.delete(f"/api/core/favoritos/{pk}/").status_code, 404)

    def test_sem_acesso_e_chaves_desconhecidas_rejeitados(self):
        dados = {"contexto":"transferencias","nome":"Consulta","filtros":{"credencial":"indevida"}}
        self.assertEqual(self.client.post("/api/core/favoritos/", dados, format="json").status_code, 400)
        self.acesso.modulos = ["cargas"]
        self.acesso.permissoes = {"cargas":["consultar"]}
        self.acesso.save()
        dados["filtros"] = {"search":"soja"}
        self.assertEqual(self.client.post("/api/core/favoritos/", dados, format="json").status_code, 400)

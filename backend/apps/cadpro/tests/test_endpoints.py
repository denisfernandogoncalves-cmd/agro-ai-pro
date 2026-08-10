from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.propriedades.models import Propriedade

from ..models import CADPro, CADProPropriedade


class CADProEndpointTests(APITestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(
            username="cadpro-teste", password="senha-segura"
        )
        self.propriedade = Propriedade.objects.create(
            nome="Fazenda API",
            municipio="Londrina",
            uf="PR",
            area_hectares="50.00",
        )

    def test_endpoints_exigem_autenticacao(self):
        cad_pro = CADPro.objects.create(codigo="1000001", descricao="Titular")
        for metodo, url, dados in (
            (self.client.get, "/api/cadpros/", None),
            (self.client.post, "/api/cadpros/", {}),
            (self.client.get, f"/api/cadpros/{cad_pro.pk}/", None),
            (self.client.patch, f"/api/cadpros/{cad_pro.pk}/", {}),
            (self.client.get, f"/api/cadpros/{cad_pro.pk}/propriedades/", None),
            (self.client.post, f"/api/cadpros/{cad_pro.pk}/propriedades/", {}),
            (self.client.post, f"/api/cadpros/{cad_pro.pk}/inativar/", {}),
        ):
            resposta = metodo(url, dados, format="json") if dados is not None else metodo(url)
            self.assertEqual(resposta.status_code, 401, (metodo, url, resposta.data))

    def test_fluxo_completo_sem_delete_publico(self):
        self.client.force_authenticate(self.usuario)
        criacao = self.client.post(
            "/api/cadpros/",
            {"codigo": " 123.456-7 ", "descricao": "Produtor V1", "ativo": False},
            format="json",
        )
        self.assertEqual(criacao.status_code, 201, criacao.data)
        cad_pro_id = criacao.data["id"]
        self.assertEqual(criacao.data["codigo_normalizado"], "1234567")
        self.assertTrue(criacao.data["ativo"])
        lista = self.client.get("/api/cadpros/?search=123.456")
        self.assertEqual(lista.status_code, 200)
        self.assertEqual(len(lista.data), 1)
        self.assertEqual(self.client.get(f"/api/cadpros/{cad_pro_id}/").status_code, 200)
        atualizacao = self.client.patch(
            f"/api/cadpros/{cad_pro_id}/",
            {"descricao": "Produtor atualizado", "ativo": False},
            format="json",
        )
        self.assertEqual(atualizacao.status_code, 200, atualizacao.data)
        self.assertEqual(atualizacao.data["descricao"], "Produtor atualizado")
        self.assertTrue(atualizacao.data["ativo"])
        vinculo = self.client.post(
            f"/api/cadpros/{cad_pro_id}/propriedades/",
            {"propriedade": self.propriedade.pk},
            format="json",
        )
        self.assertEqual(vinculo.status_code, 201, vinculo.data)
        self.assertEqual(vinculo.data["propriedade"], self.propriedade.pk)
        propriedades = self.client.get(f"/api/cadpros/{cad_pro_id}/propriedades/")
        self.assertEqual(propriedades.status_code, 200)
        self.assertEqual(len(propriedades.data), 1)
        self.assertEqual(self.client.delete(f"/api/cadpros/{cad_pro_id}/").status_code, 405)
        self.assertEqual(
            self.client.put(
                f"/api/cadpros/{cad_pro_id}/",
                {"codigo": "9999999", "descricao": "PUT"},
                format="json",
            ).status_code,
            405,
        )
        inativacao = self.client.post(
            f"/api/cadpros/{cad_pro_id}/inativar/", {}, format="json"
        )
        self.assertEqual(inativacao.status_code, 200)
        self.assertFalse(inativacao.data["ativo"])
        self.assertEqual(CADProPropriedade.objects.count(), 1)
        outra = Propriedade.objects.create(
            nome="Outra Fazenda", municipio="Londrina", area_hectares="10.00"
        )
        bloqueado = self.client.post(
            f"/api/cadpros/{cad_pro_id}/propriedades/",
            {"propriedade": outra.pk},
            format="json",
        )
        self.assertEqual(bloqueado.status_code, 400, bloqueado.data)

    def test_codigo_normalizado_duplicado_e_rejeitado(self):
        self.client.force_authenticate(self.usuario)
        CADPro.objects.create(codigo="123-4567", descricao="Primeiro")
        resposta = self.client.post(
            "/api/cadpros/",
            {"codigo": "123.456/7", "descricao": "Segundo"},
            format="json",
        )
        self.assertEqual(resposta.status_code, 400)
        self.assertIn("codigo", resposta.data)

    def test_schema_documenta_rotas_cadpro(self):
        self.client.force_authenticate(self.usuario)
        resposta = self.client.get("/api/schema.json")
        self.assertEqual(resposta.status_code, 200)
        self.assertIn("/cadpros/", resposta.data["paths"])
        self.assertIn("/cadpros/{id}/inativar/", resposta.data["paths"])
        self.assertIn("/cadpros/{id}/propriedades/", resposta.data["paths"])

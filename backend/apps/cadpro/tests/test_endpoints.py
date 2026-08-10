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
            {"descricao": "Produtor atualizado", "ativuïmm¢G§²ÚîÆ­yØØYÜ›ÏXØYÜ›Ëˆ›ÜšYYYOXÜšX\—Ü›ÜšYYYJ•°ë[˜İ[È[˜]]›ÈŠKˆ]]›ÏQ˜[ÙKˆ
B‚ˆYˆ\İØØY›×Ú[˜]]›×Ü™\Ù\˜Wİš[˜İ[×Ú\İÜšXÛ×ÜÙ[WÜ\›Z]\—Ü™X]]˜XØ[ÊÙ[ŠN‚ˆØYÜ›ÈHĞQ›Ë›Øš™XİË˜Ü™X]JÛÙYÛÏHNNNNNNH‹\ØÜšXØ[ÏH’\İ0ìÜšXÛÈŠBˆš[˜İ[ÈHĞQ›Ô›ÜšYYYK›Øš™XİË˜Ü™X]JˆØYÜ›ÏXØYÜ›Ëˆ›ÜšYYYOXÜšX\—Ü›ÜšYYYJ
Kˆ
BˆØYÜ›Ë˜]]›ÈH˜[ÙBˆØYÜ›ËœØ]™J
Bˆš[˜İ[ËœØ]™J
Bˆš[˜İ[Ë˜]]›ÈH˜[ÙBˆš[˜İ[ËœØ]™J
Bˆš[˜İ[Ë˜]]›ÈHYBˆÚ]Ù[‹˜\ÜÙ\˜Z\Ù\Ê˜[Y][Û‘\œ›ÜŠN‚ˆš[˜İ[ËœØ]™J
B
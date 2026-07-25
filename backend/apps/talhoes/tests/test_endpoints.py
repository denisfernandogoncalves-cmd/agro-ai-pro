import shutil

from django.conf import settings
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.propriedades.models import Propriedade
from apps.talhoes.tests.factories import kml_upload


@override_settings(MEDIA_ROOT=settings.BASE_DIR / "test-media-talhoes")
class TalhaoEndpointTests(TestCase):
    def setUp(self):
        self.propriedade = Propriedade.objects.create(nome="Fazenda", municipio="Londrina", area_hectares=100)
        self.client = APIClient()

    def tearDown(self):
        shutil.rmtree(settings.BASE_DIR / "test-media-talhoes", ignore_errors=True)

    def test_cria_e_lista_talhao_com_dados_para_mapa(self):
        resposta = self.client.post("/api/talhoes/talhoes/", {"nome": "Norte", "area_hectares": "20", "propriedade": self.propriedade.pk, "arquivo_kml": kml_upload()}, format="multipart")
        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.assertEqual(resposta.data["geometria_geojson"]["type"], "Polygon")
        lista = self.client.get("/api/talhoes/talhoes/")
        self.assertEqual(lista.status_code, 200)
        self.assertEqual(lista.data[0]["propriedade_nome"], "Fazenda")

    def test_retorna_400_para_kml_invalido(self):
        resposta = self.client.post("/api/talhoes/talhoes/", {"nome": "Norte", "area_hectares": "20", "propriedade": self.propriedade.pk, "arquivo_kml": kml_upload("invalido.txt")}, format="multipart")
        self.assertEqual(resposta.status_code, 400)
        self.assertIn("extensão .kml", str(resposta.data))

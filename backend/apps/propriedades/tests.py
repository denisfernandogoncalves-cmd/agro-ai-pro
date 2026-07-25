import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.talhoes.models import Talhao

from .models import Propriedade


KML_VALIDO = b"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Placemark><Polygon><outerBoundaryIs><LinearRing><coordinates>
    -50,-20,0 -49,-20,0 -49,-19,0 -50,-19,0 -50,-20,0
  </coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark>
</kml>"""


class PropriedadeAPITests(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media_root = tempfile.mkdtemp()
        cls.override_media = override_settings(MEDIA_ROOT=cls.media_root)
        cls.override_media.enable()

    @classmethod
    def tearDownClass(cls):
        cls.override_media.disable()
        shutil.rmtree(cls.media_root, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.usuario = get_user_model().objects.create_user(
            username="gestor", password="senha-segura"
        )
        self.url = reverse("propriedade-list")
        self.dados = {
            "nome": "Fazenda Horizonte",
            "proprietario": "Maria Silva",
            "municipio": "Sorriso",
            "uf": "mt",
            "area_hectares": "1250.50",
            "latitude": "-12.542300",
            "longitude": "-55.721100",
            "observacoes": "Unidade produtiva principal.",
        }

    def test_exige_autenticacao(self):
        resposta = self.client.get(self.url)
        self.assertEqual(resposta.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_crud_de_propriedade(self):
        self.client.force_authenticate(self.usuario)

        criacao = self.client.post(self.url, self.dados, format="json")
        self.assertEqual(criacao.status_code, status.HTTP_201_CREATED)
        self.assertEqual(criacao.data["uf"], "MT")

        detalhe_url = reverse("propriedade-detail", args=[criacao.data["id"]])
        consulta = self.client.get(detalhe_url)
        self.assertEqual(consulta.status_code, status.HTTP_200_OK)

        alteracao = self.client.patch(
            detalhe_url, {"area_hectares": "1300.00"}, format="json"
        )
        self.assertEqual(alteracao.status_code, status.HTTP_200_OK)
        self.assertEqual(alteracao.data["area_hectares"], "1300.00")

        exclusao = self.client.delete(detalhe_url)
        self.assertEqual(exclusao.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Propriedade.objects.filter(pk=criacao.data["id"]).exists())

    def test_valida_area_e_uf(self):
        self.client.force_authenticate(self.usuario)
        dados = {
            **self.dados,
            "area_hectares": "0",
            "uf": "M1",
        }

        resposta = self.client.post(self.url, dados, format="json")

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("area_hectares", resposta.data)
        self.assertIn("uf", resposta.data)

    def test_valida_par_de_coordenadas(self):
        self.client.force_authenticate(self.usuario)
        dados = {**self.dados, "longitude": None}

        resposta = self.client.post(self.url, dados, format="json")

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", resposta.data)

    def test_upload_kml_calcula_centroide(self):
        self.client.force_authenticate(self.usuario)
        dados = {
            "nome": "Fazenda KML",
            "municipio": "Sinop",
            "uf": "MT",
            "area_hectares": "10.00",
            "arquivo_kml": SimpleUploadedFile(
                "limite.kml", KML_VALIDO, content_type="application/vnd.google-earth.kml+xml"
            ),
        }

        resposta = self.client.post(self.url, dados, format="multipart")

        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        propriedade = Propriedade.objects.get(pk=resposta.data["id"])
        self.assertAlmostEqual(float(propriedade.latitude), -19.5, places=5)
        self.assertAlmostEqual(float(propriedade.longitude), -49.5, places=5)

    def test_rejeita_upload_kml_invalido(self):
        self.client.force_authenticate(self.usuario)
        dados = {
            "nome": "Fazenda inválida",
            "municipio": "Sinop",
            "uf": "MT",
            "area_hectares": "10.00",
            "arquivo_kml": SimpleUploadedFile(
                "limite.kml", b"<kml>invalido", content_type="application/xml"
            ),
        }

        resposta = self.client.post(self.url, dados, format="multipart")

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("arquivo_kml", resposta.data)
        self.assertFalse(Propriedade.objects.exists())

    def test_busca_e_ordenacao(self):
        self.client.force_authenticate(self.usuario)
        Propriedade.objects.create(
            nome="Boa Esperança", municipio="Lucas do Rio Verde", uf="MT", area_hectares=50
        )
        Propriedade.objects.create(
            nome="Aurora", municipio="Sorriso", uf="MT", area_hectares=100
        )

        resposta = self.client.get(self.url, {"search": "Sorriso", "ordering": "-area_hectares"})

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resposta.data), 1)
        self.assertEqual(resposta.data[0]["nome"], "Aurora")

    def test_nao_exclui_propriedade_com_talhao(self):
        self.client.force_authenticate(self.usuario)
        propriedade = Propriedade.objects.create(
            nome="Fazenda Protegida", municipio="Sorriso", uf="MT", area_hectares=100
        )
        Talhao.objects.create(
            propriedade=propriedade, nome="Talhão 1", area_hectares=20
        )

        resposta = self.client.delete(reverse("propriedade-detail", args=[propriedade.pk]))

        self.assertEqual(resposta.status_code, status.HTTP_409_CONFLICT)
        self.assertTrue(Propriedade.objects.filter(pk=propriedade.pk).exists())

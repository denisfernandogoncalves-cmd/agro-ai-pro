import shutil

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.propriedades.models import Propriedade
from apps.talhoes.models import Talhao
from apps.talhoes.tests.factories import kml_upload


@override_settings(MEDIA_ROOT=settings.BASE_DIR / "test-media-talhoes")
class TalhaoEndpointTests(TestCase):
    def setUp(self):
        self.propriedade = Propriedade.objects.create(nome="Fazenda", municipio="Londrina", area_hectares=100)
        self.client = APIClient()
        self.client.force_authenticate(
            get_user_model().objects.create_user(username="gestor-talhoes")
        )

    def tearDown(self):
        shutil.rmtree(settings.BASE_DIR / "test-media-talhoes", ignore_errors=True)

    def test_exige_autenticacao(self):
        self.client.force_authenticate(user=None)

        resposta_talhoes = self.client.get("/api/talhoes/talhoes/")
        resposta_historicos = self.client.get(
            "/api/talhoes/historicos-agronomicos/"
        )

        self.assertEqual(resposta_talhoes.status_code, 401)
        self.assertEqual(resposta_historicos.status_code, 401)

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

    def test_filtra_busca_ordena_e_pagina_talhoes(self):
        outra_propriedade = Propriedade.objects.create(
            nome="Outra Fazenda",
            municipio="Sorriso",
            area_hectares=100,
        )
        Talhao.objects.create(
            propriedade=self.propriedade,
            nome="Norte",
            area_hectares=20,
            cultura_atual="Soja",
            safra="2025/2026",
        )
        Talhao.objects.create(
            propriedade=self.propriedade,
            nome="Sul",
            area_hectares=30,
            cultura_atual="Soja",
            safra="2025/2026",
        )
        Talhao.objects.create(
            propriedade=outra_propriedade,
            nome="Milho",
            area_hectares=10,
            cultura_atual="Milho",
            safra="2025/2026",
        )

        resposta = self.client.get(
            "/api/talhoes/talhoes/",
            {
                "propriedade": self.propriedade.pk,
                "cultura": "soja",
                "search": "Norte",
                "ordering": "-area_hectares",
                "page_size": 1,
            },
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.data["count"], 1)
        self.assertEqual(resposta.data["results"][0]["nome"], "Norte")

    def test_crud_de_historico_agronomico(self):
        talhao = Talhao.objects.create(
            propriedade=self.propriedade,
            nome="Norte",
            area_hectares=20,
        )
        url = "/api/talhoes/historicos-agronomicos/"

        criacao = self.client.post(
            url,
            {
                "talhao": talhao.pk,
                "data_referencia": "2026-07-25",
                "cultura": "Soja",
                "safra": "2025/2026",
                "produtividade_esperada": "65.00",
                "produtividade_realizada": "62.50",
                "observacoes": "Colheita encerrada.",
            },
            format="json",
        )
        self.assertEqual(criacao.status_code, 201, criacao.data)

        lista = self.client.get(url, {"talhao": talhao.pk})
        self.assertEqual(lista.status_code, 200)
        self.assertEqual(len(lista.data), 1)
        self.assertEqual(lista.data[0]["talhao_nome"], "Norte")

        detalhe = f"{url}{criacao.data['id']}/"
        alteracao = self.client.patch(
            detalhe,
            {"produtividade_realizada": "63.00"},
            format="json",
        )
        self.assertEqual(alteracao.status_code, 200)
        self.assertEqual(alteracao.data["produtividade_realizada"], "63.00")

        exclusao = self.client.delete(detalhe)
        self.assertEqual(exclusao.status_code, 204)

    def test_nao_exclui_talhao_com_historico(self):
        talhao = Talhao.objects.create(
            propriedade=self.propriedade,
            nome="Norte",
            area_hectares=20,
        )
        self.client.post(
            "/api/talhoes/historicos-agronomicos/",
            {
                "talhao": talhao.pk,
                "data_referencia": "2026-07-25",
                "cultura": "Soja",
            },
            format="json",
        )

        resposta = self.client.delete(f"/api/talhoes/talhoes/{talhao.pk}/")

        self.assertEqual(resposta.status_code, 409)
        self.assertTrue(Talhao.objects.filter(pk=talhao.pk).exists())

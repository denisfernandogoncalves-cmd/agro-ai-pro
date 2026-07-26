from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from apps.propriedades.models import Propriedade

from .models import PrevisaoClima
from .services import (
    ServicoClimaError,
    atualizar_previsoes,
    buscar_previsoes,
    gerar_alerta_agricola,
)


def resposta_open_meteo(chuva=12.5):
    return {
        "daily": {
            "time": ["2026-07-26", "2026-07-27"],
            "weather_code": [61, 2],
            "temperature_2m_max": [29.4, 31.0],
            "temperature_2m_min": [17.1, 18.2],
            "precipitation_sum": [chuva, 0],
            "precipitation_probability_max": [80, 10],
            "wind_speed_10m_max": [21.2, 18.0],
            "relative_humidity_2m_mean": [74, 61],
        }
    }


class ClimaServiceTests(TestCase):
    def setUp(self):
        self.propriedade = Propriedade.objects.create(
            nome="Fazenda Clima",
            municipio="Sorriso",
            area_hectares=100,
            latitude="-12.500000",
            longitude="-55.700000",
        )

    def test_normaliza_previsao_e_parametros_do_provedor(self):
        recebido = {}

        def transport(parametros):
            recebido.update(parametros)
            return resposta_open_meteo()

        previsoes = buscar_previsoes(
            self.propriedade.latitude,
            self.propriedade.longitude,
            transport=transport,
        )

        self.assertEqual(len(previsoes), 2)
        self.assertEqual(previsoes[0]["condicao"], "Chuva fraca")
        self.assertEqual(previsoes[0]["umidade"], 74)
        self.assertEqual(previsoes[0]["chuva_mm"], Decimal("12.50"))
        self.assertEqual(recebido["timezone"], "America/Sao_Paulo")
        self.assertIn("relative_humidity_2m_mean", recebido["daily"])

    def test_atualizacao_e_idempotente(self):
        atualizar_previsoes(
            self.propriedade,
            transport=lambda _: resposta_open_meteo(chuva=10),
        )
        atualizar_previsoes(
            self.propriedade,
            transport=lambda _: resposta_open_meteo(chuva=22),
        )

        self.assertEqual(PrevisaoClima.objects.count(), 2)
        self.assertEqual(
            PrevisaoClima.objects.get(data=date(2026, 7, 26)).chuva_mm,
            Decimal("22.00"),
        )

    def test_exige_coordenadas_da_propriedade(self):
        self.propriedade.latitude = None
        self.propriedade.longitude = None

        with self.assertRaisesMessage(ServicoClimaError, "latitude e longitude"):
            atualizar_previsoes(self.propriedade, transport=lambda _: {})

    def test_gera_alertas_agricolas_combinados(self):
        alerta = gerar_alerta_agricola(
            {
                "temperatura_min": Decimal("2"),
                "temperatura_max": Decimal("36"),
                "chuva_mm": Decimal("55"),
                "vento_kmh": Decimal("45"),
                "umidade": 25,
            }
        )

        self.assertIn("Risco de geada", alerta)
        self.assertIn("Chuva intensa", alerta)
        self.assertIn("Umidade baixa", alerta)

    def test_rejeita_series_inconsistentes(self):
        dados = resposta_open_meteo()
        dados["daily"]["wind_speed_10m_max"] = [10]

        with self.assertRaisesMessage(ServicoClimaError, "inconsistentes"):
            buscar_previsoes(0, 0, transport=lambda _: dados)

    def test_impede_previsao_duplicada(self):
        PrevisaoClima.objects.create(
            propriedade=self.propriedade,
            data=date(2026, 7, 26),
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            PrevisaoClima.objects.create(
                propriedade=self.propriedade,
                data=date(2026, 7, 26),
            )


class ClimaAPITests(APITestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(
            username="gestor-clima",
            password="senha-segura",
        )
        self.propriedade = Propriedade.objects.create(
            nome="Fazenda API",
            municipio="Sinop",
            area_hectares=50,
            latitude="-11.800000",
            longitude="-55.500000",
        )
        self.previsao = PrevisaoClima.objects.create(
            propriedade=self.propriedade,
            data=date(2026, 7, 26),
            temperatura_min=18,
            temperatura_max=30,
            chuva_mm=5,
            umidade=70,
            vento_kmh=15,
            condicao="Parcialmente nublado",
        )

    def test_exige_autenticacao(self):
        resposta = self.client.get("/api/clima/previsoes/")
        self.assertEqual(resposta.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_lista_e_filtra_por_propriedade(self):
        outra = Propriedade.objects.create(
            nome="Outra",
            municipio="Sinop",
            area_hectares=20,
        )
        PrevisaoClima.objects.create(
            propriedade=outra,
            data=date(2026, 7, 26),
        )
        self.client.force_authenticate(self.usuario)

        resposta = self.client.get(
            "/api/clima/previsoes/",
            {"propriedade": self.propriedade.pk},
        )

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resposta.data), 1)
        self.assertEqual(resposta.data[0]["propriedade_nome"], "Fazenda API")

    @patch("apps.clima.views.atualizar_previsoes")
    def test_atualiza_previsao_por_propriedade(self, atualizar_mock):
        atualizar_mock.return_value = [self.previsao]
        self.client.force_authenticate(self.usuario)

        resposta = self.client.post(
            "/api/clima/previsoes/atualizar/",
            {"propriedade": self.propriedade.pk},
            format="json",
        )

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resposta.data), 1)
        atualizar_mock.assert_called_once_with(self.propriedade)

    def test_atualizacao_exige_propriedade(self):
        self.client.force_authenticate(self.usuario)
        resposta = self.client.post(
            "/api/clima/previsoes/atualizar/",
            {},
            format="json",
        )
        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("apps.clima.views.atualizar_previsoes")
    def test_trata_indisponibilidade_do_provedor(self, atualizar_mock):
        atualizar_mock.side_effect = ServicoClimaError("Serviço indisponível.")
        self.client.force_authenticate(self.usuario)

        resposta = self.client.post(
            "/api/clima/previsoes/atualizar/",
            {"propriedade": self.propriedade.pk},
            format="json",
        )

        self.assertEqual(
            resposta.status_code,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )
        self.assertEqual(resposta.data["detail"], "Serviço indisponível.")

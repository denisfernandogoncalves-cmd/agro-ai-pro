from datetime import timedelta
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.propriedades.models import AcessoPropriedade, Propriedade

from .models import (
    AlertaClimatico,
    AtualizacaoClima,
    ConfiguracaoClima,
    PrevisaoClima,
    PrevisaoHoraria,
)
from .services import (
    ServicoClimaError,
    _consultar_cacheado,
    atualizar_clima_propriedade,
    obter_coordenadas_propriedade,
)


def resposta_completa(chuva=12.0, codigo=61):
    horas = [f"2026-07-27T{hora:02d}:00" for hora in range(24)]
    return {
        "current": {
            "time": "2026-07-27T10:00",
            "temperature_2m": 24.5,
            "relative_humidity_2m": 72,
            "apparent_temperature": 25.1,
            "precipitation": 0.0,
            "weather_code": codigo,
            "cloud_cover": 40,
            "pressure_msl": 1014.2,
            "wind_speed_10m": 9.5,
            "wind_direction_10m": 125,
            "wind_gusts_10m": 18.0,
        },
        "hourly": {
            "time": horas,
            "temperature_2m": [24.0] * 24,
            "relative_humidity_2m": [72] * 24,
            "dew_point_2m": [18.0] * 24,
            "apparent_temperature": [25.0] * 24,
            "precipitation_probability": [20] * 24,
            "precipitation": [0.0] * 24,
            "weather_code": [codigo] * 24,
            "cloud_cover": [40] * 24,
            "pressure_msl": [1014.0] * 24,
            "wind_speed_10m": [9.0] * 24,
            "wind_direction_10m": [125] * 24,
            "wind_gusts_10m": [18.0] * 24,
            "shortwave_radiation": [400.0] * 24,
            "et0_fao_evapotranspiration": [0.1] * 24,
        },
        "daily": {
            "time": ["2026-07-27", "2026-07-28"],
            "weather_code": [codigo, 2],
            "temperature_2m_max": [31.0, 30.0],
            "temperature_2m_min": [17.0, 18.0],
            "apparent_temperature_max": [33.0, 31.0],
            "apparent_temperature_min": [17.0, 18.0],
            "precipitation_sum": [chuva, 0.0],
            "precipitation_probability_max": [80, 10],
            "wind_speed_10m_max": [21.0, 18.0],
            "wind_gusts_10m_max": [32.0, 25.0],
            "wind_direction_10m_dominant": [130, 140],
            "relative_humidity_2m_mean": [74, 65],
            "pressure_msl_mean": [1013.0, 1015.0],
            "cloud_cover_mean": [60, 30],
            "shortwave_radiation_sum": [18.0, 21.0],
            "dew_point_2m_mean": [18.0, 16.0],
            "et0_fao_evapotranspiration": [3.5, 4.0],
            "sunrise": ["2026-07-27T06:50", "2026-07-28T06:50"],
            "sunset": ["2026-07-27T17:55", "2026-07-28T17:56"],
        },
    }


class ClimaAutomaticoServiceTests(TestCase):
    def setUp(self):
        cache.clear()
        self.propriedade = Propriedade.objects.create(
            nome="Fazenda Automática",
            municipio="Ivaiporã",
            uf="PR",
            area_hectares=120,
            latitude="-24.245000",
            longitude="-51.675000",
        )

    def test_atualiza_estado_atual_horario_diario_e_agendamento(self):
        resultado = atualizar_clima_propriedade(
            self.propriedade,
            transport=lambda _: resposta_completa(),
            force=True,
        )
        configuracao = ConfiguracaoClima.objects.get(propriedade=self.propriedade)
        self.assertEqual(len(resultado["previsoes"]), 2)
        self.assertEqual(PrevisaoHoraria.objects.filter(propriedade=self.propriedade).count(), 24)
        self.assertEqual(configuracao.status, ConfiguracaoClima.Status.ATUALIZADO)
        self.assertEqual(configuracao.dados_atuais["temperatura"], 24.5)
        self.assertEqual(configuracao.origem_coordenadas, "cadastro")
        self.assertGreater(configuracao.proxima_atualizacao, configuracao.ultima_atualizacao)
        self.assertEqual(AtualizacaoClima.objects.filter(status="sucesso").count(), 1)

    def test_nao_repete_chamada_dentro_da_frequencia(self):
        transport = Mock(return_value=resposta_completa())
        atualizar_clima_propriedade(self.propriedade, transport=transport, force=True)
        resultado = atualizar_clima_propriedade(self.propriedade, transport=transport, force=False)
        self.assertTrue(resultado["ignorada"])
        self.assertEqual(transport.call_count, 1)

    def test_cache_do_provedor_e_deduplicado(self):
        parametros = {"latitude": -24.2, "longitude": -51.6}
        with patch("apps.clima.services._consultar_open_meteo") as transport:
            transport.return_value = resposta_completa()
            primeiro, primeiro_cache = _consultar_cacheado(parametros, transport, force=False)
            segundo, segundo_cache = _consultar_cacheado(parametros, transport, force=False)
        self.assertEqual(primeiro, segundo)
        self.assertFalse(primeiro_cache)
        self.assertTrue(segundo_cache)
        self.assertEqual(transport.call_count, 1)

    def test_falha_mantem_previsao_e_programa_backoff(self):
        atualizar_clima_propriedade(
            self.propriedade,
            transport=lambda _: resposta_completa(chuva=4),
            force=True,
        )
        quantidade = PrevisaoClima.objects.count()
        with self.assertRaises(ServicoClimaError):
            atualizar_clima_propriedade(
                self.propriedade,
                transport=lambda _: (_ for _ in ()).throw(TimeoutError()),
                force=True,
            )
        configuracao = ConfiguracaoClima.objects.get(propriedade=self.propriedade)
        self.assertEqual(PrevisaoClima.objects.count(), quantidade)
        self.assertEqual(configuracao.status, ConfiguracaoClima.Status.ERRO)
        self.assertEqual(configuracao.falhas_consecutivas, 1)
        self.assertGreater(configuracao.proxima_atualizacao, timezone.now())

    def test_utiliza_centroide_geojson_sem_inventar_coordenadas(self):
        self.propriedade.latitude = None
        self.propriedade.longitude = None
        self.propriedade.geometria_geojson = {
            "type": "Polygon",
            "coordinates": [[[-51.7, -24.3], [-51.5, -24.3], [-51.5, -24.1], [-51.7, -24.3]]],
        }
        self.propriedade.save()
        coordenadas = obter_coordenadas_propriedade(self.propriedade)
        self.assertEqual(coordenadas[2], "geojson_propriedade")
        self.assertAlmostEqual(coordenadas[0], -24.2, places=3)
        self.assertAlmostEqual(coordenadas[1], -51.6, places=3)

    def test_sem_localizacao_nao_chama_provedor(self):
        self.propriedade.latitude = None
        self.propriedade.longitude = None
        self.propriedade.geometria_geojson = None
        self.propriedade.save()
        transport = Mock(return_value=resposta_completa())
        with self.assertRaisesMessage(ServicoClimaError, "coordenadas"):
            atualizar_clima_propriedade(self.propriedade, transport=transport, force=True)
        self.assertFalse(transport.called)
        self.assertEqual(
            ConfiguracaoClima.objects.get(propriedade=self.propriedade).status,
            ConfiguracaoClima.Status.SEM_LOCALIZACAO,
        )

    def test_alertas_sao_gerados_sem_notificacao_externa(self):
        atualizar_clima_propriedade(
            self.propriedade,
            transport=lambda _: resposta_completa(chuva=70, codigo=96),
            force=True,
        )
        textos = " ".join(
            AlertaClimatico.objects.filter(ativo=True).values_list("descricao", flat=True)
        )
        self.assertIn("Chuva intensa", textos)
        self.assertIn("granizo", textos.lower())

    @override_settings(CLIMA_AUTOMATIC_UPDATE_ENABLED=True)
    @patch("apps.clima.management.commands.atualizar_clima.atualizar_clima_pendente")
    def test_management_command_executa_um_ciclo(self, atualizar_mock):
        atualizar_mock.return_value = {"atualizadas": 1, "ignoradas": 0, "erros": 0}
        call_command("atualizar_clima", limit=5)
        atualizar_mock.assert_called_once_with(limite=5)


class ClimaAutomaticoAPITests(APITestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(
            username="operador-clima-auto",
            password="senha-de-teste",
        )
        self.propriedade = Propriedade.objects.create(
            nome="Fazenda Permitida",
            municipio="Ivaiporã",
            uf="PR",
            area_hectares=80,
            latitude="-24.245000",
            longitude="-51.675000",
        )
        self.outra = Propriedade.objects.create(
            nome="Fazenda Externa",
            municipio="Londrina",
            uf="PR",
            area_hectares=70,
            latitude="-23.300000",
            longitude="-51.170000",
        )
        AcessoPropriedade.objects.create(
            propriedade=self.propriedade,
            usuario=self.usuario,
            papel=AcessoPropriedade.Papel.OPERADOR,
        )
        configuracao = ConfiguracaoClima.objects.create(
            propriedade=self.propriedade,
            ultima_atualizacao=timezone.now(),
            proxima_atualizacao=timezone.now() + timedelta(hours=3),
            status=ConfiguracaoClima.Status.ATUALIZADO,
            dados_atuais={"temperatura": 25, "condicao": "Céu limpo"},
        )
        PrevisaoHoraria.objects.create(
            propriedade=self.propriedade,
            data_hora=timezone.now() + timedelta(hours=1),
            temperatura=25,
            condicao_pulverizacao="favoravel",
            condicao_colheita="favoravel",
        )
        AlertaClimatico.objects.create(
            propriedade=self.propriedade,
            chave="teste",
            tipo="vento",
            nivel=AlertaClimatico.Nivel.ATENCAO,
            titulo="Vento forte",
            descricao="Atenção ao vento.",
            inicio=timezone.now(),
        )
        self.configuracao = configuracao
        self.client.force_authenticate(self.usuario)

    def test_status_horario_e_alertas_respeitam_propriedade(self):
        resposta = self.client.get(
            "/api/clima/previsoes/status/",
            {"propriedade": self.propriedade.pk},
        )
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta.data["atual"]["temperatura"], 25)
        self.assertEqual(resposta.data["alertas_ativos"], 1)
        self.assertEqual(
            self.client.get("/api/clima/horarias/", {"propriedade": self.propriedade.pk}).status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.client.get("/api/clima/alertas/", {"propriedade": self.propriedade.pk}).status_code,
            status.HTTP_200_OK,
        )

    def test_acesso_cruzado_retorna_404_ou_lista_vazia(self):
        resposta_status = self.client.get(
            "/api/clima/previsoes/status/",
            {"propriedade": self.outra.pk},
        )
        resposta_lista = self.client.get(
            "/api/clima/horarias/",
            {"propriedade": self.outra.pk},
        )
        self.assertEqual(resposta_status.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(resposta_lista.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resposta_lista.data), 0)

    def test_operador_nao_altera_limites_gerenciais(self):
        resposta = self.client.patch(
            f"/api/clima/configuracoes/{self.configuracao.pk}/",
            {"frequencia_minutos": 60},
            format="json",
        )
        self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)

    def test_respostas_nao_expoem_chaves_ou_tokens(self):
        resposta = self.client.get(
            "/api/clima/previsoes/status/",
            {"propriedade": self.propriedade.pk},
        )
        conteudo = str(resposta.data).lower()
        self.assertNotIn("apikey", conteudo)
        self.assertNotIn("authorization", conteudo)
        self.assertNotIn("token", conteudo)

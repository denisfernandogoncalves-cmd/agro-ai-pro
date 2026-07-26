"""Integração resiliente com o provedor gratuito Open-Meteo."""

from datetime import date
from decimal import Decimal
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from django.db import transaction

from .models import PrevisaoClima


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT_SEGUNDOS = 10
VARIAVEIS_DIARIAS = (
    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "precipitation_probability_max",
    "wind_speed_10m_max",
    "relative_humidity_2m_mean",
)

CONDICOES_WMO = {
    0: "Céu limpo",
    1: "Predominantemente limpo",
    2: "Parcialmente nublado",
    3: "Nublado",
    45: "Neblina",
    48: "Neblina com geada",
    51: "Garoa fraca",
    53: "Garoa moderada",
    55: "Garoa forte",
    61: "Chuva fraca",
    63: "Chuva moderada",
    65: "Chuva forte",
    80: "Pancadas de chuva fracas",
    81: "Pancadas de chuva moderadas",
    82: "Pancadas de chuva fortes",
    95: "Trovoadas",
    96: "Trovoadas com granizo",
    99: "Trovoadas fortes com granizo",
}


class ServicoClimaError(RuntimeError):
    """Falha tratada de comunicação ou contrato com o provedor climático."""


def _decimal(valor):
    return None if valor is None else Decimal(str(valor)).quantize(Decimal("0.01"))


def _inteiro(valor):
    return None if valor is None else round(float(valor))


def gerar_alerta_agricola(previsao):
    alertas = []
    if previsao["temperatura_min"] is not None and previsao["temperatura_min"] <= 3:
        alertas.append("Risco de geada")
    if previsao["temperatura_max"] is not None and previsao["temperatura_max"] >= 35:
        alertas.append("Calor intenso")
    if previsao["chuva_mm"] is not None and previsao["chuva_mm"] >= 50:
        alertas.append("Chuva intensa")
    if previsao["vento_kmh"] is not None and previsao["vento_kmh"] >= 40:
        alertas.append("Vento forte")
    if previsao["umidade"] is not None and previsao["umidade"] <= 30:
        alertas.append("Umidade baixa")
    return "; ".join(alertas)


def _normalizar_resposta(dados):
    diario = dados.get("daily")
    if not isinstance(diario, dict) or not diario.get("time"):
        raise ServicoClimaError("O provedor retornou uma previsão incompleta.")

    quantidade = len(diario["time"])
    campos = {
        "temperatura_max": diario.get("temperature_2m_max", []),
        "temperatura_min": diario.get("temperature_2m_min", []),
        "chuva_mm": diario.get("precipitation_sum", []),
        "probabilidade_chuva": diario.get("precipitation_probability_max", []),
        "vento_kmh": diario.get("wind_speed_10m_max", []),
        "umidade": diario.get("relative_humidity_2m_mean", []),
        "codigo_tempo": diario.get("weather_code", []),
    }
    if any(len(valores) != quantidade for valores in campos.values()):
        raise ServicoClimaError("O provedor retornou séries climáticas inconsistentes.")

    previsoes = []
    for indice, data_iso in enumerate(diario["time"]):
        codigo = _inteiro(campos["codigo_tempo"][indice])
        previsao = {
            "data": date.fromisoformat(data_iso),
            "temperatura_max": _decimal(campos["temperatura_max"][indice]),
            "temperatura_min": _decimal(campos["temperatura_min"][indice]),
            "chuva_mm": _decimal(campos["chuva_mm"][indice]),
            "probabilidade_chuva": _inteiro(
                campos["probabilidade_chuva"][indice]
            ),
            "vento_kmh": _decimal(campos["vento_kmh"][indice]),
            "umidade": _inteiro(campos["umidade"][indice]),
            "codigo_tempo": codigo,
            "condicao": CONDICOES_WMO.get(codigo, "Condição variável"),
            "fonte": "Open-Meteo",
        }
        previsao["alerta_agricola"] = gerar_alerta_agricola(previsao)
        previsoes.append(previsao)
    return previsoes


def _consultar_open_meteo(parametros):
    url = f"{OPEN_METEO_URL}?{urlencode(parametros)}"
    with urlopen(url, timeout=TIMEOUT_SEGUNDOS) as resposta:
        return json.loads(resposta.read().decode("utf-8"))


def buscar_previsoes(latitude, longitude, transport=_consultar_open_meteo):
    parametros = {
        "latitude": float(latitude),
        "longitude": float(longitude),
        "daily": ",".join(VARIAVEIS_DIARIAS),
        "timezone": "America/Sao_Paulo",
        "forecast_days": 7,
    }
    try:
        dados = transport(parametros)
    except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
        raise ServicoClimaError(
            "Não foi possível consultar o serviço meteorológico."
        ) from exc
    return _normalizar_resposta(dados)


@transaction.atomic
def atualizar_previsoes(propriedade, transport=_consultar_open_meteo):
    if propriedade.latitude is None or propriedade.longitude is None:
        raise ServicoClimaError(
            "A propriedade precisa ter latitude e longitude para consultar o clima."
        )
    resultados = []
    for dados in buscar_previsoes(
        propriedade.latitude,
        propriedade.longitude,
        transport=transport,
    ):
        previsao, _ = PrevisaoClima.objects.update_or_create(
            propriedade=propriedade,
            data=dados.pop("data"),
            defaults=dados,
        )
        resultados.append(previsao)
    return resultados

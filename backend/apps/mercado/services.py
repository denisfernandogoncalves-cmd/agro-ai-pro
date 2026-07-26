"""Integrações gratuitas e análises informativas do módulo de Mercado."""

import csv
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from io import StringIO
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.db import transaction

from .models import ClimaCornBelt, CotacaoMercado


TIMEOUT_SEGUNDOS = 12
FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

SERIES_MERCADO = {
    CotacaoMercado.Produto.SOJA: {
        "serie": "PSOYBUSDM",
        "unidade": "US$/tonelada métrica",
    },
    CotacaoMercado.Produto.MILHO: {
        "serie": "PMAIZMTUSDM",
        "unidade": "US$/tonelada métrica",
    },
    CotacaoMercado.Produto.TRIGO: {
        "serie": "PWHEAMTUSDM",
        "unidade": "US$/tonelada métrica",
    },
    CotacaoMercado.Produto.BRENT: {
        "serie": "POILBREUSDM",
        "unidade": "US$/barril",
    },
}

REGIOES_CORN_BELT = {
    ClimaCornBelt.Regiao.IOWA: (41.8780, -93.0977),
    ClimaCornBelt.Regiao.ILLINOIS: (40.0000, -89.2500),
    ClimaCornBelt.Regiao.INDIANA: (40.2672, -86.1349),
    ClimaCornBelt.Regiao.NEBRASKA: (41.4925, -99.9018),
    ClimaCornBelt.Regiao.MINNESOTA: (46.7296, -94.6859),
}


class ServicoMercadoError(RuntimeError):
    """Falha tratada de comunicação ou contrato com fonte externa."""


def _get_texto(url):
    requisicao = Request(url, headers={"User-Agent": "AGRO-AI-PRO/1.0"})
    with urlopen(requisicao, timeout=TIMEOUT_SEGUNDOS) as resposta:
        return resposta.read().decode("utf-8-sig")


def _get_json(url):
    return json.loads(_get_texto(url))


def _inicio_historico():
    hoje = date.today()
    return date(hoje.year - 2, hoje.month, 1)


def buscar_cotacoes(produto, transport=_get_texto):
    configuracao = SERIES_MERCADO.get(produto)
    if not configuracao:
        raise ServicoMercadoError("Produto de mercado não reconhecido.")
    parametros = urlencode(
        {
            "id": configuracao["serie"],
            "cosd": _inicio_historico().isoformat(),
        }
    )
    try:
        conteudo = transport(f"{FRED_CSV_URL}?{parametros}")
        linhas = csv.DictReader(StringIO(conteudo))
        resultados = []
        for linha in linhas:
            valor = linha.get(configuracao["serie"])
            if not valor or valor == ".":
                continue
            resultados.append(
                {
                    "produto": produto,
                    "data": date.fromisoformat(linha["observation_date"]),
                    "valor": Decimal(valor).quantize(Decimal("0.0001")),
                    "unidade": configuracao["unidade"],
                    "fonte": "FRED / FMI",
                }
            )
    except (
        HTTPError,
        URLError,
        TimeoutError,
        OSError,
        ValueError,
        KeyError,
        InvalidOperation,
    ) as exc:
        raise ServicoMercadoError(
            "Não foi possível consultar as cotações de mercado."
        ) from exc
    if not resultados:
        raise ServicoMercadoError("A fonte não retornou cotações válidas.")
    return resultados


@transaction.atomic
def atualizar_cotacoes(transport=_get_texto):
    registros = []
    for produto in SERIES_MERCADO:
        for dados in buscar_cotacoes(produto, transport=transport):
            cotacao, _ = CotacaoMercado.objects.update_or_create(
                produto=dados.pop("produto"),
                data=dados.pop("data"),
                defaults=dados,
            )
            registros.append(cotacao)
    return registros


def _alerta_corn_belt(temperatura_min, temperatura_max, precipitacao):
    alertas = []
    if temperatura_min <= 0:
        alertas.append("risco de geada")
    if temperatura_max >= 35:
        alertas.append("calor intenso")
    if precipitacao >= 50:
        alertas.append("chuva intensa")
    if precipitacao <= 1 and temperatura_max >= 30:
        alertas.append("calor com baixa precipitação")
    return "; ".join(alertas)


def buscar_clima_corn_belt(regiao, transport=_get_json):
    coordenadas = REGIOES_CORN_BELT.get(regiao)
    if not coordenadas:
        raise ServicoMercadoError("Região do Corn Belt não reconhecida.")
    parametros = urlencode(
        {
            "latitude": coordenadas[0],
            "longitude": coordenadas[1],
            "daily": (
                "temperature_2m_min,temperature_2m_max,precipitation_sum"
            ),
            "timezone": "America/Chicago",
            "forecast_days": 7,
        }
    )
    try:
        dados = transport(f"{OPEN_METEO_URL}?{parametros}")
        diario = dados["daily"]
        quantidade = len(diario["time"])
        campos = (
            diario["temperature_2m_min"],
            diario["temperature_2m_max"],
            diario["precipitation_sum"],
        )
        if any(len(campo) != quantidade for campo in campos):
            raise ValueError("séries inconsistentes")
        resultados = []
        for indice, data_iso in enumerate(diario["time"]):
            minima = Decimal(str(campos[0][indice])).quantize(Decimal("0.01"))
            maxima = Decimal(str(campos[1][indice])).quantize(Decimal("0.01"))
            chuva = Decimal(str(campos[2][indice])).quantize(Decimal("0.01"))
            resultados.append(
                {
                    "regiao": regiao,
                    "data": date.fromisoformat(data_iso),
                    "temperatura_min": minima,
                    "temperatura_max": maxima,
                    "precipitacao_mm": chuva,
                    "alerta": _alerta_corn_belt(minima, maxima, chuva),
                    "fonte": "Open-Meteo",
                }
            )
    except (
        HTTPError,
        URLError,
        TimeoutError,
        OSError,
        ValueError,
        KeyError,
        TypeError,
        InvalidOperation,
    ) as exc:
        raise ServicoMercadoError(
            "Não foi possível consultar o clima do Corn Belt."
        ) from exc
    return resultados


@transaction.atomic
def atualizar_clima_corn_belt(transport=_get_json):
    registros = []
    for regiao in REGIOES_CORN_BELT:
        for dados in buscar_clima_corn_belt(regiao, transport=transport):
            previsao, _ = ClimaCornBelt.objects.update_or_create(
                regiao=dados.pop("regiao"),
                data=dados.pop("data"),
                defaults=dados,
            )
            registros.append(previsao)
    return registros


def resumir_produto(produto):
    cotacoes = list(
        CotacaoMercado.objects.filter(produto=produto).order_by("-data")[:2]
    )
    if not cotacoes:
        return None
    atual = cotacoes[0]
    variacao = None
    tendencia = "Sem histórico suficiente"
    if len(cotacoes) == 2 and cotacoes[1].valor:
        variacao = (
            (atual.valor - cotacoes[1].valor) / cotacoes[1].valor * 100
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if variacao >= 5:
            tendencia = "Alta relevante no último período"
        elif variacao <= -5:
            tendencia = "Queda relevante no último período"
        else:
            tendencia = "Variação moderada no último período"
    return {
        "produto": produto,
        "produto_nome": atual.get_produto_display(),
        "data": atual.data,
        "valor": atual.valor,
        "unidade": atual.unidade,
        "variacao_percentual": variacao,
        "tendencia": tendencia,
        "aviso": "Indicador informativo; não constitui recomendação financeira.",
    }

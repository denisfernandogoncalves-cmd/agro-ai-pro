import csv
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from io import StringIO
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.utils import timezone

from .enterprise_models import AtivoMercado


TIMEOUT_SEGUNDOS = 15
STOOQ_QUOTE_URL = "https://stooq.com/q/l/"
STOOQ_HISTORY_URL = "https://stooq.com/q/d/l/"
BCB_PTAX_URL = (
    "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
    "CotacaoDolarPeriodo(dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)"
)


ATIVOS = {
    AtivoMercado.SOJA_CBOT: {
        "provedor": "stooq",
        "simbolo": "zs.f",
        "unidade": "US¢/bushel",
        "moeda": "USD",
    },
    AtivoMercado.MILHO_CBOT: {
        "provedor": "stooq",
        "simbolo": "zc.f",
        "unidade": "US¢/bushel",
        "moeda": "USD",
    },
    AtivoMercado.TRIGO_CBOT: {
        "provedor": "stooq",
        "simbolo": "zw.f",
        "unidade": "US¢/bushel",
        "moeda": "USD",
    },
    AtivoMercado.FARELO_SOJA: {
        "provedor": "stooq",
        "simbolo": "zm.f",
        "unidade": "US$/short ton",
        "moeda": "USD",
    },
    AtivoMercado.OLEO_SOJA: {
        "provedor": "stooq",
        "simbolo": "zl.f",
        "unidade": "US¢/lb",
        "moeda": "USD",
    },
    AtivoMercado.BRENT: {
        "provedor": "stooq",
        "simbolo": "co.f",
        "unidade": "US$/barril",
        "moeda": "USD",
    },
    AtivoMercado.DOLAR: {
        "provedor": "bcb_ptax",
        "simbolo": "USD/BRL",
        "unidade": "R$/US$",
        "moeda": "BRL",
    },
}


class ProvedorMercadoError(RuntimeError):
    pass


def obter_texto(url):
    request = Request(url, headers={"User-Agent": "AGRO-AI-PRO/1.1"})
    with urlopen(request, timeout=TIMEOUT_SEGUNDOS) as response:
        return response.read().decode("utf-8-sig")


def obter_json(url):
    return json.loads(obter_texto(url))


def _decimal(valor):
    if valor in {None, "", "N/D", "N/A", "-"}:
        return None
    return Decimal(str(valor).replace(",", "."))


def _data_hora_stooq(data, hora):
    naive = datetime.strptime(f"{data} {hora or '00:00:00'}", "%Y-%m-%d %H:%M:%S")
    return timezone.make_aware(naive, timezone.get_current_timezone())


def buscar_stooq(ativo, *, transport=obter_texto, dias=35):
    config = ATIVOS[ativo]
    simbolo = config["simbolo"]
    quote_url = f"{STOOQ_QUOTE_URL}?{urlencode({'s': simbolo, 'f': 'sd2t2ohlcv', 'h': '', 'e': 'csv'})}"
    inicio = timezone.localdate() - timedelta(days=dias + 10)
    fim = timezone.localdate()
    history_url = f"{STOOQ_HISTORY_URL}?{urlencode({'s': simbolo, 'd1': inicio.strftime('%Y%m%d'), 'd2': fim.strftime('%Y%m%d'), 'i': 'd'})}"
    try:
        quote_rows = list(csv.DictReader(StringIO(transport(quote_url))))
        history_rows = list(csv.DictReader(StringIO(transport(history_url))))
        if not quote_rows:
            raise ValueError("cotação vazia")
        quote = quote_rows[0]
        snapshot = {
            "data_hora": _data_hora_stooq(quote["Date"], quote.get("Time")),
            "abertura": _decimal(quote.get("Open")),
            "maxima": _decimal(quote.get("High")),
            "minima": _decimal(quote.get("Low")),
            "fechamento": _decimal(quote.get("Close")),
            "volume": _decimal(quote.get("Volume")),
        }
        if snapshot["fechamento"] is None:
            raise ValueError("fechamento ausente")
        diarios = []
        for row in history_rows:
            fechamento = _decimal(row.get("Close"))
            if fechamento is None:
                continue
            data_hora = timezone.make_aware(
                datetime.strptime(row["Date"], "%Y-%m-%d"),
                timezone.get_current_timezone(),
            )
            diarios.append(
                {
                    "data_hora": data_hora,
                    "abertura": _decimal(row.get("Open")),
                    "maxima": _decimal(row.get("High")),
                    "minima": _decimal(row.get("Low")),
                    "fechamento": fechamento,
                    "volume": _decimal(row.get("Volume")),
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
        raise ProvedorMercadoError("A fonte de commodities não retornou dados válidos.") from exc
    return snapshot, diarios[-dias:]


def buscar_ptax(*, transport=obter_json, dias=35):
    fim = timezone.localdate()
    inicio = fim - timedelta(days=dias + 10)
    parametros = {
        "@dataInicial": f"'{inicio:%m-%d-%Y}'",
        "@dataFinalCotacao": f"'{fim:%m-%d-%Y}'",
        "$format": "json",
        "$top": 10000,
        "$orderby": "dataHoraCotacao asc",
    }
    query = urlencode(parametros, safe="'@$, ")
    url = f"{BCB_PTAX_URL}?{query}"
    try:
        payload = transport(url)
        valores = payload.get("value", [])
        if not valores:
            raise ValueError("PTAX vazia")
        diarios_por_data = {}
        for item in valores:
            data_hora = datetime.fromisoformat(item["dataHoraCotacao"])
            if timezone.is_naive(data_hora):
                data_hora = timezone.make_aware(data_hora, timezone.get_current_timezone())
            valor = _decimal(item.get("cotacaoVenda"))
            if valor is None:
                continue
            diarios_por_data[data_hora.date()] = {
                "data_hora": data_hora,
                "abertura": valor,
                "maxima": valor,
                "minima": valor,
                "fechamento": valor,
                "volume": None,
            }
        diarios = list(diarios_por_data.values())[-dias:]
        if not diarios:
            raise ValueError("PTAX sem valores")
        snapshot = diarios[-1].copy()
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
        raise ProvedorMercadoError("O Banco Central não retornou a PTAX esperada.") from exc
    return snapshot, diarios

"""Cotações CBOT com atraso, separadas dos indicadores mensais FRED/FMI."""
from datetime import datetime, timezone as datetime_timezone
from decimal import Decimal, InvalidOperation
import json
import re
from urllib.parse import quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from django.db import transaction
from django.utils import timezone
from .models import CotacaoCBOT
from .services import ServicoMercadoError

SIMBOLOS = {"soja": "ZS=F", "milho": "ZC=F", "trigo": "ZW=F"}
NOMES = {"soja": "Soybean", "milho": "Corn", "trigo": "Chicago SRW Wheat"}


def consultar_provedor(simbolo):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(simbolo, safe='')}?interval=1d&range=1d"
    with urlopen(Request(url, headers={"User-Agent": "AGRO-AI-PRO/1.0"}), timeout=12) as resposta:
        conteudo = resposta.read(1_000_001)
        if len(conteudo) > 1_000_000:
            raise ValueError("Resposta excede o limite de leitura.")
        return json.loads(conteudo)


def normalizar_cotacao(produto, dados):
    try:
        if dados["chart"].get("error"):
            raise ValueError("Falha do provedor.")
        meta = dados["chart"]["result"][0]["meta"]
        if meta["symbol"] != SIMBOLOS[produto] or meta["exchangeName"] != "CBT" or meta["currency"] != "USX":
            raise ValueError("Símbolo, bolsa ou unidade não conferem.")
        contrato = meta["shortName"]
        if not re.fullmatch(NOMES[produto]+r" Futures,\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)-\d{1,4}", contrato):
            raise ValueError("Contrato de referência não identificado.")
        preco = Decimal(str(meta["regularMarketPrice"]))
        if not preco.is_finite() or preco <= 0 or preco >= Decimal("1000000000000"):
            raise ValueError("Preço inválido.")
        if preco != preco.quantize(Decimal("0.0001")):
            raise ValueError("Precisão não reconhecida.")
        instante = datetime.fromtimestamp(int(meta["regularMarketTime"]), tz=datetime_timezone.utc)
        if instante > timezone.now() or instante.year < 2000:
            raise ValueError("Instante da cotação inválido.")
        return {"produto":produto, "simbolo":SIMBOLOS[produto], "contrato":contrato,
                "cotado_em":instante, "valor_centavos_bushel":preco,
                "valor_usd_bushel":(preco/Decimal("100")).quantize(Decimal("0.000001")),
                "fonte":"Yahoo Finance / CBOT"}
    except (KeyError, IndexError, TypeError, ValueError, InvalidOperation, OverflowError) as exc:
        raise ServicoMercadoError("A cotação CBOT não trouxe preço, unidade, contrato e horário válidos. Os dados anteriores foram preservados.") from exc


def atualizar_cbot(transport=consultar_provedor):
    try:
        dados = [normalizar_cotacao(produto, transport(simbolo)) for produto, simbolo in SIMBOLOS.items()]
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        raise ServicoMercadoError("Não foi possível atualizar a CBOT pelo provedor gratuito. Tente novamente mais tarde; as cotações anteriores foram preservadas.") from exc
    # Todas as respostas são validadas antes de persistir; reenvios não duplicam instantes.
    with transaction.atomic():
        for item in dados:
            CotacaoCBOT.objects.get_or_create(produto=item["produto"], contrato=item["contrato"], cotado_em=item["cotado_em"], defaults={k:v for k,v in item.items() if k not in {"produto","contrato","cotado_em"}})
    return ultimas_cotacoes()


def ultimas_cotacoes():
    return [cotacao for produto in SIMBOLOS if (cotacao := CotacaoCBOT.objects.filter(produto=produto).order_by("-cotado_em", "-id").first())]

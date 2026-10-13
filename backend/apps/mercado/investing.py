"""Consulta limitada das páginas públicas; não utiliza API privada nem credenciais."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone as utc
from decimal import Decimal, InvalidOperation
import json
import re
from urllib.request import Request, urlopen
from django.core.cache import cache
from django.utils import timezone

REFERENCIAS = {
    "soja": ("commodities/us-soybeans", "8916", "ZS (S)", "Soja"),
    "milho": ("commodities/us-corn", "8918", "ZC (C)", "Milho"),
    "trigo": ("commodities/us-wheat", "8917", "ZW (W)", "Trigo Chicago"),
    "dolar": ("currencies/usd-brl", "2103", "USD/BRL", "Dólar USD/BRL"),
}
INTERVALO = 60


def consultar_pagina(produto):
    url = "https://br.investing.com/" + REFERENCIAS[produto][0]
    with urlopen(Request(url, headers={"User-Agent": "AGRO-AI-PRO/1.0"}), timeout=8) as resposta:
        conteudo = resposta.read(3_000_001)
        if len(conteudo) > 3_000_000:
            raise ValueError("Resposta excede limite.")
        return conteudo.decode("utf-8")


def normalizar(produto, pagina):
    try:
        match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', pagina, re.S)
        dados = json.loads(match.group(1))["props"]["pageProps"]["state"]
        instrumento = dados["currencyStore" if produto == "dolar" else "commodityStore"]["instrument"]
        base, nome, preco = instrumento["base"], instrumento["name"], instrumento["price"]
        caminho, identidade, codigo, rotulo = REFERENCIAS[produto]
        if str(base["id"]) != identidade or base["path"] != "/" + caminho:
            raise ValueError("Identidade divergente.")
        if produto == "dolar":
            if nome["shortName"] != codigo or preco["currency"] != "BRL" or base["type"] != "currency":
                raise ValueError("Par ou moeda divergente.")
        elif (nome["base_symbol"] != codigo or preco["currency"] != "USD"
              or instrumento["commodityData"]["unit"] != "_instr_unit_bushel" or base["type"] != "commodity"):
            raise ValueError("Produto ou unidade divergente.")
        valor = Decimal(str(preco["last"]))
        if not valor.is_finite() or valor <= 0 or valor >= Decimal("1000000"):
            raise ValueError("Preço inválido.")
        instante = datetime.fromtimestamp(int(preco["lastUpdateTime"]) / 1000, tz=utc.utc)
        if instante.year < 2000 or instante > timezone.now():
            raise ValueError("Horário inválido.")
        if not all(isinstance(v, bool) for v in (base["isCfd"], base["isOpen"], preco["isDelayed"])):
            raise ValueError("Natureza do dado não informada.")
        return {"produto": produto, "nome": rotulo, "simbolo": codigo, "fonte": "Investing.com",
                "url": "https://br.investing.com/" + caminho, "valor_original": str(valor),
                "valor": str(valor if produto == "dolar" else valor / 100),
                "unidade": "R$/US$" if produto == "dolar" else "US$/bushel",
                "cotado_em": instante.isoformat(), "consultado_em": timezone.now().isoformat(),
                "derivado": base["isCfd"], "atraso_provedor": preco["isDelayed"],
                "mercado_aberto": base["isOpen"], "erro": ""}
    except (AttributeError, KeyError, TypeError, ValueError, InvalidOperation, OverflowError, IndexError) as exc:
        raise ValueError("Preço, identidade, unidade ou horário não conferem.") from exc


def consultar_referencia(produto, transport=consultar_pagina):
    chave = "investing:v1:" + produto
    ultimo = cache.get(chave)
    if cache.get(chave + ":aguardar"):
        return ultimo or {"produto": produto, "nome": REFERENCIAS[produto][3], "erro": "Consulta em andamento ou indisponível."}
    if not cache.add(chave + ":trava", True, timeout=20):
        return ultimo or {"produto": produto, "nome": REFERENCIAS[produto][3], "erro": "Consulta em andamento."}
    try:
        atual = normalizar(produto, transport(produto))
        # Resposta antiga não substitui uma cotação mais recente já consultada.
        if ultimo and ultimo.get("cotado_em", "") > atual["cotado_em"]:
            atual = {**ultimo, "erro": "O provedor retornou um horário anterior; último preço preservado."}
        cache.set(chave, atual, timeout=604800)
        cache.set(chave + ":aguardar", True, timeout=INTERVALO)
        return atual
    except (OSError, ValueError, TimeoutError):
        aviso = "Investing indisponível; último preço preservado com seu horário original."
        atual = {**(ultimo or {"produto": produto, "nome": REFERENCIAS[produto][3]}), "erro": aviso}
        cache.set(chave, atual, timeout=604800)
        cache.set(chave + ":aguardar", True, timeout=300)
        return atual
    finally:
        cache.delete(chave + ":trava")


def consultar_referencias():
    with ThreadPoolExecutor(max_workers=4) as executor:
        dados = list(executor.map(consultar_referencia, REFERENCIAS))
    return {"cotacoes": dados, "intervalo_segundos": INTERVALO,
            "aviso": "Último valor disponível nas páginas públicas; sem garantia de tempo real. Grãos derivados dos futuros de Chicago, não ajuste oficial."}

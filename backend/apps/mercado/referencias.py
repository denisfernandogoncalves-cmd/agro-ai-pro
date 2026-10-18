"""Referências gratuitas de Chicago, sem gravar registros operacionais."""
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote

from django.core.cache import cache
from django.utils import timezone

from .cbot import SIMBOLOS, consultar_provedor, normalizar_cotacao
from .investing import INTERVALO, REFERENCIAS, consultar_referencia
from .services import ServicoMercadoError


def consultar_chicago(produto, transport=None):
    chave = "yahoo:cbot:v1:" + produto
    ultimo = cache.get(chave)
    vazio = {"produto": produto, "nome": REFERENCIAS[produto][3]}
    if cache.get(chave + ":aguardar"):
        return ultimo or {**vazio, "erro": "Consulta em andamento ou indisponível."}
    if not cache.add(chave + ":trava", True, timeout=30):
        return ultimo or {**vazio, "erro": "Consulta em andamento."}
    try:
        dado = normalizar_cotacao(produto, (transport or consultar_provedor)(SIMBOLOS[produto]))
        atual = {
            **vazio, "simbolo": dado["simbolo"], "contrato": dado["contrato"],
            "fonte": dado["fonte"],
            "url": "https://finance.yahoo.com/quote/" + quote(dado["simbolo"], safe="") + "/",
            "valor": str(dado["valor_usd_bushel"]),
            "valor_original": str(dado["valor_centavos_bushel"]),
            "unidade": "US$/bushel", "cotado_em": dado["cotado_em"].isoformat(),
            "consultado_em": timezone.now().isoformat(), "derivado": False,
            "atraso_provedor": True, "erro": "",
        }
        if ultimo and ultimo.get("cotado_em", "") > atual["cotado_em"]:
            atual = {**ultimo, "erro": "O provedor retornou um horário anterior; último preço preservado."}
        cache.set(chave, atual, timeout=604800)
        cache.set(chave + ":aguardar", True, timeout=INTERVALO)
        return atual
    except (OSError, ValueError, TimeoutError, ServicoMercadoError):
        atual = {**(ultimo or vazio), "erro": "Yahoo Finance indisponível; último preço preservado com seu horário original."}
        cache.set(chave, atual, timeout=604800)
        cache.set(chave + ":aguardar", True, timeout=300)
        return atual
    finally:
        cache.delete(chave + ":trava")


def consultar_referencias():
    with ThreadPoolExecutor(max_workers=4) as executor:
        tarefas = [executor.submit(consultar_chicago, produto) for produto in SIMBOLOS]
        dolar = executor.submit(consultar_referencia, "dolar")
        dados = [tarefa.result() for tarefa in tarefas] + [dolar.result()]
    return {"cotacoes": dados, "intervalo_segundos": INTERVALO,
            "aviso": "Futuros CBOT via Yahoo Finance com atraso; dólar USD/BRL via Investing.com. Não são preços de ajuste oficial."}

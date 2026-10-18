"""Calendário nacional; pontos facultativos e feriados locais não são incluídos."""
from datetime import date, timedelta
from functools import lru_cache


@lru_cache(maxsize=64)
def feriados_nacionais(ano):
    # Páscoa gregoriana (algoritmo de Meeus/Jones/Butcher).
    a, b, c = ano % 19, ano // 100, ano % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    pascoa = date(ano, (h + l - 7 * m + 114) // 31, (h + l - 7 * m + 114) % 31 + 1)
    fixos = {(1, 1), (4, 21), (5, 1), (9, 7), (10, 12), (11, 2), (11, 15), (12, 25)}
    if ano >= 2024:
        fixos.add((11, 20))
    return {date(ano, mes, dia) for mes, dia in fixos} | {pascoa - timedelta(days=2)}


def vencimento_dia_util(data_compra, prazo):
    if prazo is None:
        return None
    vencimento = data_compra + timedelta(days=prazo)
    while vencimento.weekday() >= 5 or vencimento in feriados_nacionais(vencimento.year):
        vencimento += timedelta(days=1)
    return vencimento

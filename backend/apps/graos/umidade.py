from decimal import Decimal


VERSAO_TABELA_UMIDADE = "2026-08-20"
UMIDADE_MINIMA = Decimal("11.5")
UMIDADE_MAXIMA = Decimal("30.0")

_VALORES_SOJA_MILHO = (
    "0", "0", "0", "0", "0", "0", "1", "1.75", "2.5", "3.25",
    "4", "4.75", "5.5", "6.25", "7", "7.75", "8.5", "9.25", "10",
    "10.75", "11.5", "12.25", "13", "13.75", "14.5", "15.25", "16",
    "16.75", "17.5", "18.25", "19", "19.75", "20.5", "21.25", "22",
    "22.75", "23.5", "24.25",
)
_VALORES_TRIGO = (
    "0", "0", "0", "0", "1", "1.75", "2.5", "3.25", "4", "4.75",
    "5.5", "6.25", "7", "7.75", "8.5", "9.25", "10", "10.75", "11.5",
    "12.25", "13", "13.75", "14.5", "15.25", "16", "16.75", "17.5",
    "18.25", "19", "19.75", "20.5", "21.25", "22", "22.75", "23.5",
    "24.25", "25", "25.75",
)


def _montar_tabela(valores):
    return {
        UMIDADE_MINIMA + Decimal(indice) / Decimal("2"): Decimal(valor)
        for indice, valor in enumerate(valores)
    }


TABELA_UMIDADE = {
    "SOJA_MILHO": _montar_tabela(_VALORES_SOJA_MILHO),
    "TRIGO": _montar_tabela(_VALORES_TRIGO),
}


class UmidadeForaDaTabelaError(ValueError):
    pass


def grupo_cultural(cultura):
    cultura_normalizada = " ".join(str(cultura or "").strip().upper().split())
    if cultura_normalizada in {"SOJA", "MILHO"}:
        return "SOJA_MILHO"
    if cultura_normalizada == "TRIGO":
        return "TRIGO"
    raise UmidadeForaDaTabelaError(
        "A tabela de umidade está disponível somente para Soja, Milho e Trigo."
    )


def obter_desconto_umidade(*, cultura, umidade_percentual):
    umidade = Decimal(str(umidade_percentual))
    if umidade < UMIDADE_MINIMA or umidade > UMIDADE_MAXIMA:
        raise UmidadeForaDaTabelaError(
            "A umidade deve estar entre 11,5% e 30%, conforme a tabela oficial."
        )
    grupo = grupo_cultural(cultura)
    try:
        desconto = TABELA_UMIDADE[grupo][umidade]
    except KeyError as exc:
        raise UmidadeForaDaTabelaError(
            "Informe a umidade em intervalos exatos de 0,5 ponto percentual."
        ) from exc
    return grupo, umidade, desconto

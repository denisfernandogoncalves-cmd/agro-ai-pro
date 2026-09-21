from django.db.models import F, Q, QuerySet

from .models import (
    MovimentacaoGraos,
    OrigemSaldoGraos,
    PosicaoSaldoGraos,
    ReservaSaldoGraos,
)


def filtrar_cargas_por_produtor(queryset, *, propriedade="", cad_pro=""):
    dimensoes = {}
    if propriedade:
        dimensoes["propriedade_id"] = propriedade
    if cad_pro:
        dimensoes["cad_pro_id"] = cad_pro
    if not dimensoes:
        return queryset
    # Uma única condição exige que propriedade e CAD/PRO pertençam à mesma parcela.
    parcelas = {f"rateios__{campo}": valor for campo, valor in dimensoes.items()}
    return queryset.filter(
        Q(**parcelas) | Q(rateios__isnull=True, **dimensoes)
    ).distinct()


def selecionar_posicoes(
    *,
    cad_pro=None,
    propriedade=None,
    cultura="",
    safra="",
    classificacao_codigo="",
    armazem=None,
) -> QuerySet:
    queryset = PosicaoSaldoGraos.objects.select_related(
        "propriedade",
        "cad_pro",
        "armazem",
    ).annotate(saldo_disponivel=F("saldo_fisico_kg") - F("saldo_comprometido_kg"))
    if cad_pro:
        queryset = queryset.filter(cad_pro_id=cad_pro)
    if propriedade:
        queryset = queryset.filter(propriedade_id=propriedade)
    if cultura:
        queryset = queryset.filter(cultura__iexact=cultura.strip())
    if safra:
        queryset = queryset.filter(safra=safra.strip())
    if classificacao_codigo:
        queryset = queryset.filter(
            classificacao_codigo=classificacao_codigo.strip().upper()
        )
    if armazem:
        queryset = queryset.filter(armazem_id=armazem)
    return queryset


def selecionar_origens() -> QuerySet:
    return OrigemSaldoGraos.objects.select_related("criado_por").prefetch_related(
        "movimentacoes"
    )


def selecionar_reservas(*, posicao=None, status="") -> QuerySet:
    queryset = ReservaSaldoGraos.objects.select_related(
        "posicao",
        "posicao__propriedade",
        "posicao__cad_pro",
        "posicao__armazem",
        "origem",
        "criado_por",
    )
    if posicao:
        queryset = queryset.filter(posicao_id=posicao)
    if status:
        queryset = queryset.filter(status=status)
    return queryset


def selecionar_movimentacoes_saldo() -> QuerySet:
    return MovimentacaoGraos.objects.select_related(
        "lote",
        "lote__propriedade",
        "posicao",
        "posicao__propriedade",
        "posicao__cad_pro",
        "posicao__armazem",
        "origem",
        "reserva",
        "estorno_de",
        "estorno_de__carga_colhida",
        "estorno_de__carga_colhida__propriedade",
        "estorno_de__carga_colhida__cad_pro",
        "estorno_de__rateio_carga_colhida__carga",
        "estorno_de__rateio_carga_colhida__propriedade",
        "estorno_de__rateio_carga_colhida__cad_pro",
        "movimento_estorno",
        "criado_por",
        "carga_colhida",
        "carga_colhida__propriedade",
        "carga_colhida__cad_pro",
        "rateio_carga_colhida__carga",
        "rateio_carga_colhida__propriedade",
        "rateio_carga_colhida__cad_pro",
    )

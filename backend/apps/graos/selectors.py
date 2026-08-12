from django.db.models import F, QuerySet

from .models import (
    MovimentacaoGraos,
    OrigemSaldoGraos,
    PosicaoSaldoGraos,
    ReservaSaldoGraos,
)


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
        "cad_pro",
        "armazem",
        "armazem__propriedade",
    ).annotate(saldo_disponivel=F("saldo_fisico_kg") - F("saldo_comprometido_kg"))
    if cad_pro:
        queryset = queryset.filter(cad_pro_id=cad_pro)
    if propriedade:
        queryset = queryset.filter(armazem__propriedade_id=propriedade)
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
        "posicao",
        "posicao__cad_pro",
        "posicao__armazem",
        "origem",
        "reserva",
        "estorno_de",
        "criado_por",
    )

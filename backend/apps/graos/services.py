from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Case, DecimalField, F, Q, Sum, Value, When
from django.db.models.functions import Coalesce

from .models import ArmazemGraos, LoteGraos, MovimentacaoGraos


class SaldoGraosInsuficienteError(ValueError):
    pass


class CapacidadeArmazemExcedidaError(ValueError):
    pass


class MovimentacaoGraosConflitanteError(ValueError):
    pass


CAMPO_QUANTIDADE = DecimalField(max_digits=16, decimal_places=3)


def _saldo_agregado(queryset):
    return queryset.aggregate(
        saldo=Coalesce(
            Sum(
                Case(
                    When(
                        tipo=MovimentacaoGraos.Tipo.ENTRADA,
                        then=F("quantidade_kg"),
                    ),
                    default=-F("quantidade_kg"),
                    output_field=CAMPO_QUANTIDADE,
                )
            ),
            Value(Decimal("0")),
            output_field=CAMPO_QUANTIDADE,
        )
    )["saldo"]


def saldo_lote(lote):
    return _saldo_agregado(lote.movimentacoes.all())


def saldo_armazem(armazem):
    return _saldo_agregado(
        MovimentacaoGraos.objects.filter(lote__armazem=armazem)
    )


def _normalizar_quantidade(valor):
    try:
        quantidade = Decimal(str(valor))
    except (InvalidOperation, TypeError) as exc:
        raise ValueError("Quantidade inválida.") from exc
    if quantidade <= 0:
        raise ValueError("A quantidade deve ser maior que zero.")
    return quantidade


def _movimento_idempotente_existente(chave, *, lote, tipo, quantidade):
    if not chave:
        return None
    existente = MovimentacaoGraos.objects.filter(
        chave_idempotencia=chave
    ).first()
    if not existente:
        return None
    if (
        existente.lote_id != lote.id
        or existente.tipo != tipo
        or existente.quantidade_kg != quantidade
    ):
        raise MovimentacaoGraosConflitanteError(
            "A chave de idempotência já foi usada por outra movimentação."
        )
    return existente


@transaction.atomic
def registrar_movimentacao(*, usuario, tipo, lote, quantidade_kg, **dados):
    quantidade = _normalizar_quantidade(quantidade_kg)
    lote = (
        LoteGraos.objects.select_for_update()
        .select_related("armazem")
        .get(pk=lote.pk)
    )
    armazem = ArmazemGraos.objects.select_for_update().get(pk=lote.armazem_id)
    chave = (dados.get("chave_idempotencia") or "").strip() or None
    existente = _movimento_idempotente_existente(
        chave,
        lote=lote,
        tipo=tipo,
        quantidade=quantidade,
    )
    if existente:
        return existente
    if not lote.ativo or not armazem.ativo:
        raise ValueError("O lote e o armazém precisam estar ativos.")
    if tipo == MovimentacaoGraos.Tipo.SAIDA:
        disponivel = saldo_lote(lote)
        if quantidade > disponivel:
            raise SaldoGraosInsuficienteError(
                f"Saldo insuficiente. Disponível: {disponivel} kg."
            )
    elif tipo == MovimentacaoGraos.Tipo.ENTRADA:
        ocupacao = saldo_armazem(armazem)
        if ocupacao + quantidade > armazem.capacidade_kg:
            disponivel = armazem.capacidade_kg - ocupacao
            raise CapacidadeArmazemExcedidaError(
                f"Capacidade insuficiente. Disponível: {disponivel} kg."
            )
    else:
        raise ValueError("Tipo de movimentação inválido.")

    movimento = MovimentacaoGraos(
        lote=lote,
        tipo=tipo,
        quantidade_kg=quantidade,
        criado_por=usuario,
        chave_idempotencia=chave,
        **{campo: valor for campo, valor in dados.items() if campo != "chave_idempotencia"},
    )
    movimento.full_clean()
    movimento.save()
    return movimento


@transaction.atomic
def transferir_graos(
    *,
    usuario,
    lote_origem,
    lote_destino,
    quantidade_kg,
    data_movimento,
    observacoes="",
    chave_idempotencia="",
):
    if lote_origem.pk == lote_destino.pk:
        raise ValueError("Os lotes de origem e destino devem ser diferentes.")
    lotes = {
        lote.id: lote
        for lote in LoteGraos.objects.select_for_update()
        .select_related("armazem")
        .filter(id__in=(lote_origem.pk, lote_destino.pk))
        .order_by("id")
    }
    origem = lotes.get(lote_origem.pk)
    destino = lotes.get(lote_destino.pk)
    if not origem or not destino:
        raise ValueError("Lote de origem ou destino não encontrado.")
    if (origem.cultura, origem.safra) != (destino.cultura, destino.safra):
        raise ValueError("A transferência exige lotes da mesma cultura e safra.")
    list(
        ArmazemGraos.objects.select_for_update()
        .filter(id__in=(origem.armazem_id, destino.armazem_id))
        .order_by("id")
    )

    chave_base = chave_idempotencia.strip()
    referencia = f"Transferência do lote {origem.codigo} para {destino.codigo}"
    saida = registrar_movimentacao(
        usuario=usuario,
        tipo=MovimentacaoGraos.Tipo.SAIDA,
        lote=origem,
        quantidade_kg=quantidade_kg,
        data_movimento=data_movimento,
        referencia_externa=referencia,
        observacoes=observacoes,
        chave_idempotencia=f"{chave_base}:saida" if chave_base else "",
    )
    entrada = registrar_movimentacao(
        usuario=usuario,
        tipo=MovimentacaoGraos.Tipo.ENTRADA,
        lote=destino,
        quantidade_kg=quantidade_kg,
        data_movimento=data_movimento,
        referencia_externa=referencia,
        observacoes=observacoes,
        chave_idempotencia=f"{chave_base}:entrada" if chave_base else "",
    )
    return saida, entrada


def posicao_graos(queryset=None, *, propriedade=None, armazem=None, cultura="", safra=""):
    lotes = queryset if queryset is not None else LoteGraos.objects.all()
    lotes = lotes.select_related("armazem", "armazem__propriedade", "talhao")
    if propriedade:
        lotes = lotes.filter(armazem__propriedade_id=propriedade)
    if armazem:
        lotes = lotes.filter(armazem_id=armazem)
    if cultura:
        lotes = lotes.filter(cultura__iexact=cultura)
    if safra:
        lotes = lotes.filter(safra=safra)

    lotes = lotes.annotate(
        total_entradas=Coalesce(
            Sum(
                "movimentacoes__quantidade_kg",
                filter=Q(movimentacoes__tipo=MovimentacaoGraos.Tipo.ENTRADA),
            ),
            Value(Decimal("0")),
            output_field=CAMPO_QUANTIDADE,
        ),
        total_saidas=Coalesce(
            Sum(
                "movimentacoes__quantidade_kg",
                filter=Q(movimentacoes__tipo=MovimentacaoGraos.Tipo.SAIDA),
            ),
            Value(Decimal("0")),
            output_field=CAMPO_QUANTIDADE,
        ),
    )
    return [
        {
            "lote_id": lote.id,
            "codigo": lote.codigo,
            "cultura": lote.cultura,
            "safra": lote.safra,
            "armazem_id": lote.armazem_id,
            "armazem": lote.armazem.nome,
            "propriedade_id": lote.armazem.propriedade_id,
            "propriedade": lote.armazem.propriedade.nome,
            "entradas_kg": lote.total_entradas,
            "saidas_kg": lote.total_saidas,
            "saldo_kg": lote.total_entradas - lote.total_saidas,
            "ativo": lote.ativo,
        }
        for lote in lotes
    ]


def resumo_graos(**filtros):
    posicoes = posicao_graos(**filtros)
    return {
        "lotes": len(posicoes),
        "lotes_com_saldo": sum(item["saldo_kg"] > 0 for item in posicoes),
        "saldo_total_kg": sum(
            (item["saldo_kg"] for item in posicoes),
            Decimal("0"),
        ),
    }

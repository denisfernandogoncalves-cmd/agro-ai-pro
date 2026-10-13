from datetime import date
from decimal import Decimal
from apps.core.valores import validar_decimal
from django.core.exceptions import ValidationError as DjangoValidationError

from django.db import transaction
from django.db.models import Q, Sum

from .models import LancamentoFinanceiro


class OperacaoFinanceiraError(ValueError):
    pass


@transaction.atomic
def liquidar_lancamento(lancamento, *, data_liquidacao, valor_liquidado):
    lancamento = LancamentoFinanceiro.objects.select_for_update().get(
        pk=lancamento.pk
    )
    if lancamento.status != LancamentoFinanceiro.Status.PENDENTE:
        raise OperacaoFinanceiraError("Somente lançamentos pendentes podem ser liquidados.")
    if not isinstance(data_liquidacao, date):
        raise OperacaoFinanceiraError("Informe uma data de liquidação válida.")
    try:
        valor = validar_decimal(valor_liquidado,max_digits=14,decimal_places=2,minimo=Decimal("0.01"))
    except Exception as exc:
        raise OperacaoFinanceiraError("Informe um valor de liquidação válido.") from exc
    if valor <= 0:
        raise OperacaoFinanceiraError("O valor liquidado deve ser positivo.")
    lancamento.status = LancamentoFinanceiro.Status.LIQUIDADO
    lancamento.data_liquidacao = data_liquidacao
    lancamento.valor_liquidado = valor
    try:
        lancamento.full_clean()
    except DjangoValidationError as exc:
        raise OperacaoFinanceiraError("Dados de liquidação inválidos para este lançamento.") from exc
    lancamento.save(
        update_fields=(
            "status",
            "data_liquidacao",
            "valor_liquidado",
            "atualizado_em",
        )
    )
    return lancamento


@transaction.atomic
def cancelar_lancamento(lancamento):
    lancamento = LancamentoFinanceiro.objects.select_for_update().get(
        pk=lancamento.pk
    )
    if lancamento.status != LancamentoFinanceiro.Status.PENDENTE:
        raise OperacaoFinanceiraError("Somente lançamentos pendentes podem ser cancelados.")
    lancamento.status = LancamentoFinanceiro.Status.CANCELADO
    lancamento.save(update_fields=("status", "atualizado_em"))
    return lancamento


def resumo_financeiro(queryset):
    pendentes = queryset.filter(status=LancamentoFinanceiro.Status.PENDENTE)
    liquidados = queryset.filter(status=LancamentoFinanceiro.Status.LIQUIDADO)
    pagar = pendentes.filter(tipo=LancamentoFinanceiro.Tipo.PAGAR).aggregate(
        total=Sum("valor")
    )["total"] or Decimal("0")
    receber = pendentes.filter(tipo=LancamentoFinanceiro.Tipo.RECEBER).aggregate(
        total=Sum("valor")
    )["total"] or Decimal("0")
    entradas = liquidados.filter(tipo=LancamentoFinanceiro.Tipo.RECEBER).aggregate(
        total=Sum("valor_liquidado")
    )["total"] or Decimal("0")
    saidas = liquidados.filter(tipo=LancamentoFinanceiro.Tipo.PAGAR).aggregate(
        total=Sum("valor_liquidado")
    )["total"] or Decimal("0")
    hoje = date.today()
    atrasados = pendentes.filter(data_vencimento__lt=hoje).aggregate(
        total=Sum("valor")
    )["total"] or Decimal("0")
    return {
        "a_pagar": pagar,
        "a_receber": receber,
        "saldo_previsto": receber - pagar,
        "entradas_realizadas": entradas,
        "saidas_realizadas": saidas,
        "saldo_realizado": entradas - saidas,
        "valor_atrasado": atrasados,
        "quantidade_pendente": pendentes.count(),
    }

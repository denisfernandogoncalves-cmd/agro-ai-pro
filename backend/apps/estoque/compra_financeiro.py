"""Compra e estorno na mesma transação de estoque e financeiro."""
from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.db.models import Sum
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from apps.financeiro.models import LancamentoFinanceiro
from apps.financeiro.services import cancelar_lancamento, liquidar_lancamento
from .models import CompraEstoque


def valores_compra(compra):
    quantidade = sum((e.quantidade for e in compra.estornos.all()), Decimal("0"))
    estornado = (compra.valor_total * quantidade / compra.movimento.quantidade).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return estornado, compra.valor_total - estornado


def salvar_conta(conta):
    try:
        conta.full_clean()
    except DjangoValidationError as exc:
        raise serializers.ValidationError(exc.message_dict) from exc
    conta.save()


@transaction.atomic
def sincronizar_compra_financeiro(compra, estorno=None):
    origem = CompraEstoque.objects.select_for_update(of=("self",)).select_related("movimento__lote__produto", "movimento__lote__fornecedor").get(pk=compra.pk)
    if not origem.integrar_financeiro and not origem.conta_pagar_id:
        return None
    devolvido, liquido = valores_compra(origem)
    conta = LancamentoFinanceiro.objects.select_for_update().get(pk=origem.conta_pagar_id) if origem.conta_pagar_id else None
    pago_historico = origem.valor_pago if origem.data_pagamento else None
    if conta is None and origem.valor_total > 0:
        conta = LancamentoFinanceiro(tipo="pagar", descricao=f"Compra de insumos — {origem.movimento.lote.produto.nome} · {origem.pk}"[:220],
            valor=origem.valor_total if pago_historico else (liquido or origem.valor_total),
            parceiro_id=origem.movimento.lote.fornecedor_id, recebedor_nome=origem.movimento.lote.fornecedor.nome,
            safra=origem.movimento.safra, data_emissao=origem.movimento.data_movimento,
            data_vencimento=origem.data_vencimento or origem.movimento.data_movimento,
            observacoes=f"Origem: compra de estoque {origem.pk}. Sem vencimento informado, usa a data da compra. Original: {origem.valor_total}.")
        salvar_conta(conta)
        origem.conta_pagar = conta
        origem.save(update_fields=("conta_pagar",))
        if pago_historico and pago_historico > 0:
            conta = liquidar_lancamento(conta, data_liquidacao=origem.data_pagamento, valor_liquidado=pago_historico)
    if conta and conta.status == "pendente" and pago_historico and pago_historico > 0:
        conta = liquidar_lancamento(conta, data_liquidacao=origem.data_pagamento, valor_liquidado=pago_historico)
    if conta and conta.status == "pendente":
        if liquido == 0:
            cancelar_lancamento(conta)
        else:
            conta.valor = liquido
            salvar_conta(conta)
    elif conta and conta.status == "cancelado" and liquido > 0:
        raise serializers.ValidationError("A conta desta compra foi cancelada no Financeiro. Confira o título antes de alterar a compra.")
    if conta and conta.status == "liquidado":
        creditado = origem.estornos.aggregate(total=Sum("conta_receber__valor"))["total"] or Decimal("0")
        credito = min(max(conta.valor - liquido, Decimal("0")), conta.valor_liquidado) - creditado
        if credito > 0:
            if estorno is None:
                estorno = origem.estornos.filter(conta_receber__isnull=True).order_by("-criado_em").first()
            if estorno is None or estorno.conta_receber_id:
                raise serializers.ValidationError("Confira os créditos já vinculados aos estornos desta compra.")
            credito_conta = LancamentoFinanceiro(tipo="receber", descricao=f"Crédito por estorno de insumos · {origem.pk}"[:220],
                valor=credito, parceiro_id=conta.parceiro_id, recebedor_nome=conta.recebedor_nome,
                data_emissao=estorno.movimento.data_movimento, data_vencimento=estorno.movimento.data_movimento,
                safra=origem.movimento.safra, observacoes=f"Estorno {estorno.pk} da compra {origem.pk}. {estorno.motivo}")
            salvar_conta(credito_conta)
            estorno.conta_receber = credito_conta
            estorno.save(update_fields=("conta_receber",))
    compra.conta_pagar_id = origem.conta_pagar_id
    return conta

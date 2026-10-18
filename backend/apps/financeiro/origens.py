"""Títulos vinculados à origem; nenhuma baixa automática."""
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from .models import LancamentoFinanceiro
from .services import cancelar_lancamento


def sincronizar_conta_origem(origem, dados, observacoes):
    # Chamador mantém a origem bloqueada na mesma transação.
    conta = LancamentoFinanceiro.objects.select_for_update().get(pk=origem.conta_pagar_id) if origem.conta_pagar_id else None
    if origem.excluido_em:
        if conta and conta.status == LancamentoFinanceiro.Status.LIQUIDADO:
            raise serializers.ValidationError('Este registro possui conta liquidada. Trate a liquidação no Financeiro antes de excluir.')
        if conta and conta.status == LancamentoFinanceiro.Status.PENDENTE:
            cancelar_lancamento(conta)
        return
    if dados is None:
        if conta:
            raise serializers.ValidationError('Informe o vencimento: este registro já possui conta a pagar.')
        return
    if dados['valor'] <= 0 and conta is None:
        return
    if conta and conta.status != LancamentoFinanceiro.Status.PENDENTE:
        if any(getattr(conta, k) != v for k, v in dados.items()):
            raise serializers.ValidationError('O título financeiro foi liquidado ou cancelado. Esta alteração exige conferência no Financeiro.')
        return
    nova = conta is None
    if nova:
        conta = LancamentoFinanceiro(**dados, observacoes=observacoes)
    else:
        for k, v in dados.items():
            setattr(conta, k, v)
    try:
        conta.full_clean()
    except DjangoValidationError as exc:
        raise serializers.ValidationError(exc.message_dict) from exc
    if nova:
        conta.save()
        origem.conta_pagar = conta
        origem.save(update_fields=('conta_pagar',))
    else:
        conta.save(update_fields=(*dados.keys(), 'atualizado_em'))

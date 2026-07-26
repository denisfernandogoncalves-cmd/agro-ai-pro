from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.estoque.models import MovimentacaoEstoque
from apps.estoque.services import registrar_movimentacao

from .models import OperacaoAgricola


class TransicaoOperacaoError(ValueError):
    pass


@transaction.atomic
def iniciar_operacao(operacao, data_inicio=None):
    operacao = OperacaoAgricola.objects.select_for_update().get(pk=operacao.pk)
    if operacao.status != OperacaoAgricola.Status.PLANEJADA:
        raise TransicaoOperacaoError("Somente operações planejadas podem ser iniciadas.")
    operacao.status = OperacaoAgricola.Status.EM_EXECUCAO
    operacao.data_inicio = data_inicio or max(
        timezone.localdate(), operacao.data_planejada
    )
    operacao.full_clean()
    operacao.save(update_fields=("status", "data_inicio", "atualizado_em"))
    return operacao


@transaction.atomic
def concluir_operacao(operacao, *, usuario, data_conclusao=None, custo_realizado=None):
    operacao = (
        OperacaoAgricola.objects.select_for_update()
        .select_related("talhao__propriedade")
        .get(pk=operacao.pk)
    )
    if operacao.status != OperacaoAgricola.Status.EM_EXECUCAO:
        raise TransicaoOperacaoError("Somente operações em execução podem ser concluídas.")
    insumos = list(operacao.insumos.select_related("lote__produto", "lote__local"))
    for insumo in insumos:
        if insumo.movimentacao_estoque_id:
            raise TransicaoOperacaoError("Esta operação já possui baixa de estoque.")
        quantidade = insumo.quantidade_utilizada or insumo.quantidade_planejada
        movimento = registrar_movimentacao(
            usuario=usuario,
            tipo=MovimentacaoEstoque.Tipo.SAIDA,
            lote=insumo.lote,
            quantidade=quantidade,
            custo_unitario=None,
            data_movimento=data_conclusao or max(
                timezone.localdate(), operacao.data_inicio
            ),
            documento_fiscal="",
            propriedade=operacao.talhao.propriedade,
            safra=operacao.talhao.safra,
            observacoes=f"Consumo na operação #{operacao.id}: {operacao.descricao}",
        )
        insumo.quantidade_utilizada = quantidade
        insumo.movimentacao_estoque = movimento
        insumo.save(update_fields=("quantidade_utilizada", "movimentacao_estoque"))
    operacao.status = OperacaoAgricola.Status.CONCLUIDA
    operacao.data_conclusao = data_conclusao or max(
        timezone.localdate(), operacao.data_inicio
    )
    if custo_realizado not in (None, ""):
        operacao.custo_realizado = Decimal(str(custo_realizado))
    operacao.full_clean()
    operacao.save(
        update_fields=(
            "status",
            "data_conclusao",
            "custo_realizado",
            "atualizado_em",
        )
    )
    return operacao


@transaction.atomic
def cancelar_operacao(operacao):
    operacao = OperacaoAgricola.objects.select_for_update().get(pk=operacao.pk)
    if operacao.status not in {
        OperacaoAgricola.Status.PLANEJADA,
        OperacaoAgricola.Status.EM_EXECUCAO,
    }:
        raise TransicaoOperacaoError("A operação não pode ser cancelada neste estado.")
    operacao.status = OperacaoAgricola.Status.CANCELADA
    operacao.save(update_fields=("status", "atualizado_em"))
    return operacao

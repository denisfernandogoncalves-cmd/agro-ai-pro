from django.db import transaction
from django.dispatch import Signal


saldo_graos_alterado = Signal()


def publicar_apos_commit(*, nome, origem, posicoes, movimentos=(), reserva=None):
    """Agenda um evento interno somente depois da confirmação da transação."""
    payload = {
        "nome": nome,
        "origem_id": origem.pk,
        "chave_idempotencia": origem.chave_idempotencia,
        "posicoes_ids": tuple(posicao.pk for posicao in posicoes),
        "movimentacoes_ids": tuple(movimento.pk for movimento in movimentos),
        "reserva_id": reserva.pk if reserva else None,
    }
    transaction.on_commit(
        lambda: saldo_graos_alterado.send(
            sender=publicar_apos_commit,
            **payload,
        )
    )

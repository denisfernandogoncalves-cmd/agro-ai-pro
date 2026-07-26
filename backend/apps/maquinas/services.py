from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .models import Maquina, ManutencaoMaquina


class HorimetroInvalidoError(ValueError):
    pass


@transaction.atomic
def atualizar_horimetro(maquina, valor):
    maquina = Maquina.objects.select_for_update().get(pk=maquina.pk)
    novo = Decimal(str(valor))
    if novo < maquina.horimetro_atual:
        raise HorimetroInvalidoError(
            f"O horímetro não pode regredir. Atual: {maquina.horimetro_atual}."
        )
    if novo > maquina.horimetro_atual:
        maquina.horimetro_atual = novo
        maquina.save(update_fields=("horimetro_atual", "atualizado_em"))
    return maquina


@transaction.atomic
def concluir_manutencao(manutencao, *, data=None, horimetro=None, custo=None):
    manutencao = ManutencaoMaquina.objects.select_for_update().select_related(
        "maquina"
    ).get(pk=manutencao.pk)
    if manutencao.status != ManutencaoMaquina.Status.AGENDADA:
        raise ValueError("Somente manutenções agendadas podem ser concluídas.")
    valor_horimetro = horimetro or manutencao.maquina.horimetro_atual
    atualizar_horimetro(manutencao.maquina, valor_horimetro)
    manutencao.status = ManutencaoMaquina.Status.CONCLUIDA
    manutencao.data_conclusao = data or timezone.localdate()
    manutencao.horimetro_realizado = Decimal(str(valor_horimetro))
    if custo not in (None, ""):
        manutencao.custo = Decimal(str(custo))
    manutencao.save(
        update_fields=(
            "status",
            "data_conclusao",
            "horimetro_realizado",
            "custo",
        )
    )
    return manutencao

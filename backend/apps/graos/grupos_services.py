from django.db import transaction

from .models import GrupoColheita


@transaction.atomic
def inativar_grupo_colheita(grupo_id):
    grupo = GrupoColheita.objects.select_for_update().get(pk=grupo_id)
    if grupo.ativo:
        grupo.ativo = False
        grupo.save(update_fields=("ativo", "atualizado_em"))
    return grupo

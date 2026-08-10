from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction

from apps.propriedades.models import Propriedade

from .models import CADPro, CADProPropriedade


class VinculoCADProInvalido(ValueError):
    pass


def obter_cadpro_ativo(cad_pro_id):
    """Retorna o CAD/PRO ativo ou levanta CADPro.DoesNotExist."""
    try:
        return CADPro.objects.get(pk=cad_pro_id, ativo=True)
    except (DjangoValidationError, ValueError, TypeError) as exc:
        raise CADPro.DoesNotExist("CAD/PRO ativo não encontrado.") from exc


def validar_vinculo(cad_pro_id, propriedade_id):
    """Valida a origem produtiva e retorna o vínculo ativo correspondente."""
    try:
        obter_cadpro_ativo(cad_pro_id)
    except CADPro.DoesNotExist as exc:
        raise VinculoCADProInvalido("CAD/PRO ativo não encontrado.") from exc

    try:
        return CADProPropriedade.objects.select_related(
            "cad_pro",
            "propriedade",
        ).get(
            cad_pro_id=cad_pro_id,
            propriedade_id=propriedade_id,
            ativo=True,
        )
    except (
        CADProPropriedade.DoesNotExist,
        DjangoValidationError,
        ValueError,
        TypeError,
    ) as exc:
        raise VinculoCADProInvalido(
            "A propriedade não possui vínculo ativo com o CAD/PRO informado."
        ) from exc


def listar_propriedades_vinculadas(cad_pro_id):
    """Retorna as propriedades com vínculo ativo para um CAD/PRO ativo."""
    cad_pro = obter_cadpro_ativo(cad_pro_id)
    return Propriedade.objects.filter(
        vinculos_cadpro__cad_pro=cad_pro,
        vinculos_cadpro__ativo=True,
    ).order_by("nome", "id")


@transaction.atomic
def inativar_cadpro(cad_pro_id):
    cad_pro = CADPro.objects.select_for_update().get(pk=cad_pro_id)
    if cad_pro.ativo:
        cad_pro.ativo = False
        cad_pro.save(update_fields=("ativo", "atualizado_em"))
    return cad_pro

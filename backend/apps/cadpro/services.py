from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction

from apps.propriedades.models import Propriedade

from .models import CADPro, CADProPropriedade
from .models import normalizar_codigo_cadpro


class VinculoCADProInvalido(ValueError):
    pass


class CADProComSaldoError(ValueError):
    pass


class NumeroCADProInvalido(ValueError):
    pass


@transaction.atomic
def vincular_numero_cadpro_a_propriedade(*, numero, propriedade):
    """Cria ou reutiliza o CAD/PRO oficial e mantém um único vínculo ativo."""
    codigo = " ".join(str(numero or "").strip().split())
    normalizado = normalizar_codigo_cadpro(codigo)
    if not normalizado:
        raise NumeroCADProInvalido(
            "Informe um número CAD/PRO com letras ou números."
        )

    cad_pro = CADPro.objects.select_for_update().filter(
        codigo_normalizado=normalizado,
    ).first()
    if cad_pro is None:
        cad_pro = CADPro.objects.create(
            codigo=codigo,
            descricao=f"CAD/PRO da propriedade {propriedade.nome}",
        )
    elif not cad_pro.ativo:
        raise NumeroCADProInvalido(
            "O número informado pertence a um CAD/PRO inativo."
        )

    vinculo, criado = CADProPropriedade.objects.select_for_update().get_or_create(
        cad_pro=cad_pro,
        propriedade=propriedade,
    )
    if not criado and not vinculo.ativo:
        vinculo.ativo = True
        vinculo.save(update_fields=("ativo", "atualizado_em"))
    return cad_pro, vinculo


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
    from apps.graos.services import bloquear_cadpro_para_saldo

    cad_pro = bloquear_cadpro_para_saldo(cad_pro_id)
    from apps.graos.models import PosicaoSaldoGraos

    if PosicaoSaldoGraos.objects.filter(
        cad_pro=cad_pro,
        saldo_fisico_kg__gt=0,
    ).exists():
        raise CADProComSaldoError(
            "O CAD/PRO não pode ser inativado enquanto possuir saldo de grãos."
        )
    if cad_pro.ativo:
        cad_pro.ativo = False
        cad_pro.save(update_fields=("ativo", "atualizado_em"))
    return cad_pro

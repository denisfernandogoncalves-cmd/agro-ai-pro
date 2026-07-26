from django.db.models import Q
from rest_framework.exceptions import NotFound, PermissionDenied

from apps.core.access import (
    PAPEL_ADMINISTRADOR,
    PAPEIS_LEITURA,
    exigir_acesso_propriedade,
)

from .grain_models import AcessoCadPro, CadPro


def cadpros_visiveis(usuario, propriedade_id=None):
    queryset = CadPro.objects.select_related("propriedade").filter(ativo=True)
    if propriedade_id:
        queryset = queryset.filter(propriedade_id=propriedade_id)
    if usuario and usuario.is_superuser:
        return queryset
    if not usuario or not usuario.is_authenticated:
        return queryset.none()
    return queryset.filter(
        Q(
            propriedade__acessos__usuario=usuario,
            propriedade__acessos__ativo=True,
            propriedade__acessos__papel=PAPEL_ADMINISTRADOR,
        )
        | Q(acessos__usuario=usuario, acessos__ativo=True)
    ).distinct()


def exigir_acesso_cadpro(usuario, cadpro, *, papeis=PAPEIS_LEITURA, ocultar=False):
    if cadpro is None:
        raise PermissionDenied("O registro precisa estar vinculado a um CAD/PRO autorizado.")
    papel = exigir_acesso_propriedade(
        usuario,
        cadpro.propriedade,
        papeis=papeis,
        ocultar=ocultar,
    )
    if usuario and (usuario.is_superuser or papel == PAPEL_ADMINISTRADOR):
        return papel
    autorizado = AcessoCadPro.objects.filter(
        cadpro=cadpro,
        usuario=usuario,
        ativo=True,
    ).exists()
    if not autorizado:
        if ocultar:
            raise NotFound("Registro não encontrado.")
        raise PermissionDenied("Você não possui acesso a este CAD/PRO.")
    return papel


def filtrar_queryset_por_cadpro(queryset, usuario, campo="cadpro"):
    if usuario and usuario.is_superuser:
        return queryset
    ids = cadpros_visiveis(usuario).values_list("id", flat=True)
    return queryset.filter(**{f"{campo}_id__in": ids})

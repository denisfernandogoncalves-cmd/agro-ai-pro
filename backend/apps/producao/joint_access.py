from django.db.models import Q
from rest_framework.exceptions import NotFound, PermissionDenied

from apps.core.access import (
    PAPEIS_LEITURA,
    exigir_acesso_propriedade,
    ids_propriedades_usuario,
)
from apps.propriedades.models import Propriedade

from .grain_access import exigir_acesso_cadpro
from .joint_models import LoteConjuntoProducao


def lotes_conjuntos_visiveis(usuario):
    queryset = LoteConjuntoProducao.objects.all()
    ids = ids_propriedades_usuario(usuario)
    if ids is None:
        return queryset
    if not usuario or not usuario.is_authenticated:
        return queryset.none()
    nao_autorizadas = Propriedade.objects.exclude(pk__in=ids)
    return (
        queryset.exclude(participantes__propriedade__in=nao_autorizadas)
        .filter(Q(participantes__propriedade_id__in=ids) | Q(participantes__isnull=True, criado_por=usuario))
        .distinct()
    )


def exigir_acesso_lote(usuario, lote, *, papeis=PAPEIS_LEITURA, ocultar=False):
    propriedades = list(lote.participantes.select_related("propriedade").values_list("propriedade_id", flat=True))
    if not propriedades:
        if usuario and (usuario.is_superuser or lote.criado_por_id == usuario.id):
            return
        if ocultar:
            raise NotFound("Registro não encontrado.")
        raise PermissionDenied("O lote ainda não possui propriedades participantes autorizadas.")
    for propriedade_id in propriedades:
        exigir_acesso_propriedade(
            usuario,
            propriedade_id,
            papeis=papeis,
            ocultar=ocultar,
        )
    for cadpro in lote.cadpros_participantes.select_related("cadpro__propriedade"):
        exigir_acesso_cadpro(usuario, cadpro.cadpro, papeis=papeis, ocultar=ocultar)


def exigir_acesso_participante(usuario, participante, *, papeis=PAPEIS_LEITURA, ocultar=False):
    exigir_acesso_propriedade(
        usuario,
        participante.propriedade,
        papeis=papeis,
        ocultar=ocultar,
    )
    if participante.cadpro_id:
        exigir_acesso_cadpro(usuario, participante.cadpro, papeis=papeis, ocultar=ocultar)

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.access import (
    ids_propriedades_usuario,
    validar_filtro_propriedade,
)
from apps.core.query_params import obter_filtros_propriedade_safra
from apps.producao.grain_access import cadpros_visiveis

from .services import gerar_insights


class InsightsView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        filtros = obter_filtros_propriedade_safra(request.query_params)
        validar_filtro_propriedade(request.user, filtros.get("propriedade"))
        filtros["propriedades"] = ids_propriedades_usuario(request.user)
        filtros["cadpros"] = (
            None
            if request.user.is_superuser
            else list(cadpros_visiveis(request.user).values_list("id", flat=True))
        )
        return Response(gerar_insights(**filtros))

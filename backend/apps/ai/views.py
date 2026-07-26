from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.query_params import obter_filtros_propriedade_safra

from .services import gerar_insights


class InsightsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        filtros = obter_filtros_propriedade_safra(request.query_params)
        return Response(gerar_insights(**filtros))

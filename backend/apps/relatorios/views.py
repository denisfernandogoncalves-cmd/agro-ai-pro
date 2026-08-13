from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.query_params import obter_filtros_propriedade_safra

from .services import dashboard_gerencial
from .selectors import selecionar_opcoes_relatorio, selecionar_relatorio_operacional
from .serializers import FiltrosRelatorioOperacionalSerializer


class DashboardGerencialView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        filtros = obter_filtros_propriedade_safra(request.query_params)
        return Response(dashboard_gerencial(**filtros))


class RelatorioOperacionalView(APIView):
    permission_classes = [IsAuthenticated]
    http_method_names = ("get", "head", "options")

    def get(self, request):
        filtros = FiltrosRelatorioOperacionalSerializer(data=request.query_params)
        filtros.is_valid(raise_exception=True)
        return Response(selecionar_relatorio_operacional(**filtros.validated_data))


class OpcoesRelatorioOperacionalView(APIView):
    permission_classes = [IsAuthenticated]
    http_method_names = ("get", "head", "options")

    def get(self, request):
        return Response(selecionar_opcoes_relatorio())

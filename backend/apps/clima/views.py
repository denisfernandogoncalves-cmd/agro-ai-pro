from django.shortcuts import get_object_or_404
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.access import (
    PAPEIS_OPERACAO,
    exigir_acesso_propriedade,
    propriedades_visiveis,
)
from apps.core.viewsets import EscopoPropriedadeViewSetMixin

from .models import PrevisaoClima
from .serializers import PrevisaoClimaSerializer
from .services import ServicoClimaError, atualizar_previsoes


class PrevisaoClimaViewSet(
    EscopoPropriedadeViewSetMixin,
    viewsets.ReadOnlyModelViewSet,
):
    queryset = PrevisaoClima.objects.select_related("propriedade").all()
    serializer_class = PrevisaoClimaSerializer
    property_filter = "propriedade_id"
    property_path = "propriedade"
    filter_backends = (filters.OrderingFilter,)
    ordering_fields = ("data", "temperatura_min", "temperatura_max", "chuva_mm")
    ordering = ("data",)

    def get_queryset(self):
        queryset = super().get_queryset()
        propriedade = self.request.query_params.get("propriedade", "").strip()
        data_inicio = self.request.query_params.get("data_inicio", "").strip()
        data_fim = self.request.query_params.get("data_fim", "").strip()
        if propriedade:
            queryset = (
                queryset.filter(propriedade_id=propriedade)
                if propriedade.isdecimal()
                else queryset.none()
            )
        if data_inicio:
            queryset = queryset.filter(data__gte=data_inicio)
        if data_fim:
            queryset = queryset.filter(data__lte=data_fim)
        return queryset

    @action(detail=False, methods=["post"])
    def atualizar(self, request):
        propriedade_id = request.data.get("propriedade")
        if not propriedade_id:
            return Response(
                {"propriedade": ["Informe a propriedade."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        propriedade = get_object_or_404(
            propriedades_visiveis(request.user),
            pk=propriedade_id,
        )
        exigir_acesso_propriedade(
            request.user,
            propriedade,
            papeis=PAPEIS_OPERACAO,
        )
        try:
            previsoes = atualizar_previsoes(propriedade)
        except ServicoClimaError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        serializer = self.get_serializer(previsoes, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

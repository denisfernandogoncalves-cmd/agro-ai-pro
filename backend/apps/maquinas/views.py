from datetime import date

from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import AbastecimentoMaquina, Maquina, ManutencaoMaquina, UsoMaquina
from .serializers import (
    AbastecimentoMaquinaSerializer,
    MaquinaSerializer,
    ManutencaoMaquinaSerializer,
    UsoMaquinaSerializer,
)
from .services import concluir_manutencao


class MaquinaViewSet(viewsets.ModelViewSet):
    queryset = Maquina.objects.select_related("propriedade")
    serializer_class = MaquinaSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ("identificacao", "marca", "modelo")
    ordering_fields = ("identificacao", "tipo", "status", "horimetro_atual")

    def get_queryset(self):
        queryset = super().get_queryset()
        for parametro in ("tipo", "status", "propriedade"):
            valor = self.request.query_params.get(parametro, "").strip()
            if valor:
                queryset = queryset.filter(**{parametro: valor})
        return queryset


class HistoricoMaquinaMixin:
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    def update(self, request, *args, **kwargs):
        return Response(
            {"detail": "Registros históricos não podem ser editados."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def destroy(self, request, *args, **kwargs):
        return Response(
            {"detail": "Registros históricos não podem ser excluídos."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )


class UsoMaquinaViewSet(HistoricoMaquinaMixin, viewsets.ModelViewSet):
    queryset = UsoMaquina.objects.select_related("maquina", "operacao")
    serializer_class = UsoMaquinaSerializer
    search_fields = ("maquina__identificacao", "operacao__descricao", "operador")
    ordering_fields = ("data", "horimetro_final")


class AbastecimentoMaquinaViewSet(HistoricoMaquinaMixin, viewsets.ModelViewSet):
    queryset = AbastecimentoMaquina.objects.select_related("maquina")
    serializer_class = AbastecimentoMaquinaSerializer
    search_fields = ("maquina__identificacao", "documento")
    ordering_fields = ("data", "litros", "valor_total", "horimetro")


class ManutencaoMaquinaViewSet(viewsets.ModelViewSet):
    queryset = ManutencaoMaquina.objects.select_related("maquina")
    serializer_class = ManutencaoMaquinaSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ("maquina__identificacao", "descricao", "observacoes")
    ordering_fields = ("data_prevista", "status", "custo")

    def update(self, request, *args, **kwargs):
        if self.get_object().status != ManutencaoMaquina.Status.AGENDADA:
            return Response(
                {"detail": "Manutenções encerradas não podem ser editadas."},
                status=status.HTTP_409_CONFLICT,
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if self.get_object().status != ManutencaoMaquina.Status.AGENDADA:
            return Response(
                {"detail": "Manutenções encerradas não podem ser excluídas."},
                status=status.HTTP_409_CONFLICT,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["post"])
    def concluir(self, request, pk=None):
        try:
            data_conclusao = request.data.get("data_conclusao")
            manutencao = concluir_manutencao(
                self.get_object(),
                data=date.fromisoformat(data_conclusao) if data_conclusao else None,
                horimetro=request.data.get("horimetro_realizado"),
                custo=request.data.get("custo"),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(self.get_serializer(manutencao).data)

from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import ClimaCornBelt, CotacaoMercado, NoticiaMercado
from .serializers import (
    ClimaCornBeltSerializer,
    CotacaoMercadoSerializer,
    NoticiaMercadoSerializer,
)
from .services import (
    SERIES_MERCADO,
    ServicoMercadoError,
    atualizar_clima_corn_belt,
    atualizar_cotacoes,
    resumir_produto,
)


class CotacaoMercadoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CotacaoMercado.objects.all()
    serializer_class = CotacaoMercadoSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ("data", "valor", "produto")
    ordering = ("produto", "data")

    def get_queryset(self):
        queryset = super().get_queryset()
        produto = self.request.query_params.get("produto", "").strip()
        data_inicio = self.request.query_params.get("data_inicio", "").strip()
        data_fim = self.request.query_params.get("data_fim", "").strip()
        if produto:
            queryset = queryset.filter(produto=produto)
        if data_inicio:
            queryset = queryset.filter(data__gte=data_inicio)
        if data_fim:
            queryset = queryset.filter(data__lte=data_fim)
        return queryset

    @action(detail=False, methods=["post"])
    def atualizar(self, request):
        try:
            registros = atualizar_cotacoes()
        except ServicoMercadoError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({"registros_processados": len(registros)})

    @action(detail=False, methods=["get"])
    def resumo(self, request):
        resumos = [
            resumo
            for produto in SERIES_MERCADO
            if (resumo := resumir_produto(produto)) is not None
        ]
        return Response(resumos)


class ClimaCornBeltViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ClimaCornBelt.objects.all()
    serializer_class = ClimaCornBeltSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ("data", "regiao", "precipitacao_mm", "temperatura_max")
    ordering = ("regiao", "data")

    def get_queryset(self):
        queryset = super().get_queryset()
        regiao = self.request.query_params.get("regiao", "").strip()
        return queryset.filter(regiao=regiao) if regiao else queryset

    @action(detail=False, methods=["post"])
    def atualizar(self, request):
        try:
            registros = atualizar_clima_corn_belt()
        except ServicoMercadoError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({"registros_processados": len(registros)})


class NoticiaMercadoViewSet(viewsets.ModelViewSet):
    queryset = NoticiaMercado.objects.all()
    serializer_class = NoticiaMercadoSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ("titulo", "resumo", "fonte")
    ordering_fields = ("publicada_em", "fonte", "titulo")
    ordering = ("-publicada_em",)

    def get_queryset(self):
        queryset = super().get_queryset()
        ativa = self.request.query_params.get("ativa")
        if ativa in {"true", "1"}:
            queryset = queryset.filter(ativa=True)
        elif ativa in {"false", "0"}:
            queryset = queryset.filter(ativa=False)
        return queryset

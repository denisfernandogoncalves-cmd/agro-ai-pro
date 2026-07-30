from django.db.models.deletion import ProtectedError
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import ArmazemGraos, LoteGraos, MovimentacaoGraos
from .serializers import (
    ArmazemGraosSerializer,
    FiltrosGraosSerializer,
    LoteGraosSerializer,
    MovimentacaoGraosSerializer,
    TransferenciaGraosSerializer,
)
from .services import posicao_graos, resumo_graos, transferir_graos


def _filtros_posicao(query_params):
    serializer = FiltrosGraosSerializer(data=query_params)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


class CadastroGraosMixin:
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {"detail": "Este cadastro possui movimentações ou vínculos protegidos."},
                status=status.HTTP_409_CONFLICT,
            )


class ArmazemGraosViewSet(CadastroGraosMixin, viewsets.ModelViewSet):
    queryset = ArmazemGraos.objects.select_related("propriedade")
    serializer_class = ArmazemGraosSerializer
    search_fields = ("nome", "propriedade__nome")
    ordering_fields = ("nome", "capacidade_kg", "criado_em")
    ordering = ("nome", "id")

    def get_queryset(self):
        queryset = super().get_queryset()
        propriedade = self.request.query_params.get("propriedade", "").strip()
        ativo = self.request.query_params.get("ativo", "").strip().lower()
        if propriedade:
            queryset = queryset.filter(propriedade_id=propriedade)
        if ativo in {"true", "false"}:
            queryset = queryset.filter(ativo=ativo == "true")
        return queryset


class LoteGraosViewSet(CadastroGraosMixin, viewsets.ModelViewSet):
    queryset = LoteGraos.objects.select_related(
        "armazem",
        "armazem__propriedade",
        "talhao",
    )
    serializer_class = LoteGraosSerializer
    search_fields = (
        "codigo",
        "cultura",
        "safra",
        "armazem__nome",
        "armazem__propriedade__nome",
        "talhao__nome",
    )
    ordering_fields = ("codigo", "cultura", "safra", "criado_em")
    ordering = ("safra", "cultura", "codigo", "id")

    def get_queryset(self):
        queryset = super().get_queryset()
        for parametro, campo in (
            ("armazem", "armazem_id"),
            ("propriedade", "armazem__propriedade_id"),
            ("talhao", "talhao_id"),
            ("safra", "safra"),
        ):
            valor = self.request.query_params.get(parametro, "").strip()
            if valor:
                queryset = queryset.filter(**{campo: valor})
        cultura = self.request.query_params.get("cultura", "").strip()
        ativo = self.request.query_params.get("ativo", "").strip().lower()
        if cultura:
            queryset = queryset.filter(cultura__iexact=cultura)
        if ativo in {"true", "false"}:
            queryset = queryset.filter(ativo=ativo == "true")
        return queryset

    @action(detail=False, methods=["get"])
    def posicao(self, request):
        return Response(posicao_graos(**_filtros_posicao(request.query_params)))

    @action(detail=False, methods=["get"])
    def resumo(self, request):
        return Response(resumo_graos(**_filtros_posicao(request.query_params)))

    @action(detail=True, methods=["post"])
    def transferir(self, request, pk=None):
        serializer = TransferenciaGraosSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            saida, entrada = transferir_graos(
                usuario=request.user,
                lote_origem=self.get_object(),
                **serializer.validated_data,
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_409_CONFLICT,
            )
        movimento_serializer = MovimentacaoGraosSerializer(
            (saida, entrada),
            many=True,
        )
        return Response(
            {
                "saida": movimento_serializer.data[0],
                "entrada": movimento_serializer.data[1],
            },
            status=status.HTTP_201_CREATED,
        )


class MovimentacaoGraosViewSet(
    viewsets.mixins.CreateModelMixin,
    viewsets.mixins.ListModelMixin,
    viewsets.mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = MovimentacaoGraos.objects.select_related(
        "lote",
        "lote__armazem",
        "lote__armazem__propriedade",
        "criado_por",
    )
    serializer_class = MovimentacaoGraosSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = (
        "lote__codigo",
        "lote__cultura",
        "lote__safra",
        "referencia_externa",
        "observacoes",
    )
    ordering_fields = ("data_movimento", "quantidade_kg", "tipo", "criado_em")
    ordering = ("-data_movimento", "-id")

    def get_queryset(self):
        queryset = super().get_queryset()
        for parametro, campo in (
            ("tipo", "tipo"),
            ("lote", "lote_id"),
            ("armazem", "lote__armazem_id"),
            ("propriedade", "lote__armazem__propriedade_id"),
            ("safra", "lote__safra"),
        ):
            valor = self.request.query_params.get(parametro, "").strip()
            if valor:
                queryset = queryset.filter(**{campo: valor})
        cultura = self.request.query_params.get("cultura", "").strip()
        if cultura:
            queryset = queryset.filter(lote__cultura__iexact=cultura)
        return queryset

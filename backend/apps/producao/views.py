from datetime import date

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import InsumoOperacao, OperacaoAgricola
from .serializers import InsumoOperacaoSerializer, OperacaoAgricolaSerializer
from .services import (
    TransicaoOperacaoError,
    cancelar_operacao,
    concluir_operacao,
    iniciar_operacao,
)


class OperacaoAgricolaViewSet(viewsets.ModelViewSet):
    queryset = OperacaoAgricola.objects.select_related(
        "talhao__propriedade", "criado_por"
    ).prefetch_related("insumos__lote__produto", "insumos__lote__local")
    serializer_class = OperacaoAgricolaSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ("descricao", "responsavel", "talhao__nome", "observacoes")
    ordering_fields = ("data_planejada", "tipo", "status", "custo_estimado")
    ordering = ("data_planejada", "id")

    def get_queryset(self):
        queryset = super().get_queryset()
        for parametro, campo in (
            ("status", "status"),
            ("tipo", "tipo"),
            ("talhao", "talhao_id"),
            ("propriedade", "talhao__propriedade_id"),
        ):
            valor = self.request.query_params.get(parametro, "").strip()
            if valor:
                queryset = queryset.filter(**{campo: valor})
        return queryset

    def update(self, request, *args, **kwargs):
        if self.get_object().status != OperacaoAgricola.Status.PLANEJADA:
            return Response(
                {"detail": "Somente operações planejadas podem ser editadas."},
                status=status.HTTP_409_CONFLICT,
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if self.get_object().status != OperacaoAgricola.Status.PLANEJADA:
            return Response(
                {"detail": "Somente operações planejadas podem ser excluídas."},
                status=status.HTTP_409_CONFLICT,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["post"])
    def iniciar(self, request, pk=None):
        try:
            inicio = request.data.get("data_inicio")
            operacao = iniciar_operacao(
                self.get_object(),
                date.fromisoformat(inicio) if inicio else None,
            )
        except (ValueError, TransicaoOperacaoError, DjangoValidationError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(self.get_serializer(operacao).data)

    @action(detail=True, methods=["post"])
    def concluir(self, request, pk=None):
        try:
            conclusao = request.data.get("data_conclusao")
            operacao = concluir_operacao(
                self.get_object(),
                usuario=request.user,
                data_conclusao=date.fromisoformat(conclusao) if conclusao else None,
                custo_realizado=request.data.get("custo_realizado"),
            )
        except (ValueError, TransicaoOperacaoError, DjangoValidationError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(self.get_serializer(operacao).data)

    @action(detail=True, methods=["post"])
    def cancelar(self, request, pk=None):
        try:
            operacao = cancelar_operacao(self.get_object())
        except TransicaoOperacaoError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(self.get_serializer(operacao).data)


class InsumoOperacaoViewSet(viewsets.ModelViewSet):
    queryset = InsumoOperacao.objects.select_related(
        "operacao", "lote__produto", "lote__local"
    )
    serializer_class = InsumoOperacaoSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ("lote__produto__nome", "lote__codigo", "operacao__descricao")
    ordering_fields = ("quantidade_planejada", "criado_em")

    def get_queryset(self):
        queryset = super().get_queryset()
        operacao = self.request.query_params.get("operacao", "").strip()
        return queryset.filter(operacao_id=operacao) if operacao else queryset

    def update(self, request, *args, **kwargs):
        if self.get_object().operacao.status not in {
            OperacaoAgricola.Status.PLANEJADA,
            OperacaoAgricola.Status.EM_EXECUCAO,
        }:
            return Response(
                {"detail": "Os insumos desta operação estão encerrados."},
                status=status.HTTP_409_CONFLICT,
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if self.get_object().operacao.status not in {
            OperacaoAgricola.Status.PLANEJADA,
            OperacaoAgricola.Status.EM_EXECUCAO,
        }:
            return Response(
                {"detail": "Os insumos desta operação estão encerrados."},
                status=status.HTTP_409_CONFLICT,
            )
        return super().destroy(request, *args, **kwargs)

from datetime import date

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import filters, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.access import PAPEIS_GESTAO, PAPEIS_OPERACAO
from apps.core.viewsets import EscopoPropriedadeViewSetMixin

from .models import InsumoOperacao, OperacaoAgricola
from .serializers import InsumoOperacaoSerializer, OperacaoAgricolaSerializer
from .services import (
    TransicaoOperacaoError,
    cancelar_operacao,
    concluir_operacao,
    iniciar_operacao,
)


class OperacaoAgricolaViewSet(
    EscopoPropriedadeViewSetMixin,
    viewsets.ModelViewSet,
):
    queryset = OperacaoAgricola.objects.select_related(
        "talhao__propriedade",
        "criado_por",
    ).prefetch_related("insumos__lote__produto", "insumos__lote__local")
    serializer_class = OperacaoAgricolaSerializer
    property_filter = "talhao__propriedade_id"
    property_path = "talhao.propriedade"
    property_input_path = "talhao.propriedade"
    write_roles = PAPEIS_OPERACAO
    action_roles = {"destroy": PAPEIS_GESTAO}
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
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


class InsumoOperacaoViewSet(
    EscopoPropriedadeViewSetMixin,
    viewsets.ModelViewSet,
):
    queryset = InsumoOperacao.objects.select_related(
        "operacao__talhao__propriedade",
        "lote__produto",
        "lote__local__propriedade",
    )
    serializer_class = InsumoOperacaoSerializer
    property_filter = "operacao__talhao__propriedade_id"
    property_path = "operacao.talhao.propriedade"
    property_input_path = "operacao.talhao.propriedade"
    write_roles = PAPEIS_OPERACAO
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    search_fields = ("lote__produto__nome", "lote__codigo", "operacao__descricao")
    ordering_fields = ("quantidade_planejada", "criado_em")

    def get_queryset(self):
        queryset = super().get_queryset()
        operacao = self.request.query_params.get("operacao", "").strip()
        return queryset.filter(operacao_id=operacao) if operacao else queryset

    def _validar_lote(self, serializer):
        operacao = serializer.validated_data.get(
            "operacao",
            getattr(serializer.instance, "operacao", None),
        )
        lote = serializer.validated_data.get(
            "lote",
            getattr(serializer.instance, "lote", None),
        )
        if (
            operacao
            and lote
            and operacao.talhao.propriedade_id != lote.local.propriedade_id
        ):
            raise serializers.ValidationError(
                {"lote": "O lote deve pertencer à propriedade da operação."}
            )

    def perform_create(self, serializer):
        self._validar_lote(serializer)
        super().perform_create(serializer)

    def perform_update(self, serializer):
        self._validar_lote(serializer)
        super().perform_update(serializer)

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

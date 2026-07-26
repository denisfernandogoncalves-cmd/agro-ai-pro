from datetime import date

from django.db.models.deletion import ProtectedError
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    CategoriaFinanceira,
    CentroCusto,
    LancamentoFinanceiro,
    ParceiroFinanceiro,
)
from .serializers import (
    CategoriaFinanceiraSerializer,
    CentroCustoSerializer,
    LancamentoFinanceiroSerializer,
    ParceiroFinanceiroSerializer,
)
from .services import (
    OperacaoFinanceiraError,
    cancelar_lancamento,
    liquidar_lancamento,
    resumo_financeiro,
)


class CadastroFinanceiroMixin:
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    ordering = ("nome",)
    ordering_fields = ("nome", "criado_em")
    search_fields = ("nome",)

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {"detail": "Este cadastro possui lançamentos vinculados."},
                status=status.HTTP_409_CONFLICT,
            )


class CategoriaFinanceiraViewSet(CadastroFinanceiroMixin, viewsets.ModelViewSet):
    queryset = CategoriaFinanceira.objects.all()
    serializer_class = CategoriaFinanceiraSerializer


class ParceiroFinanceiroViewSet(CadastroFinanceiroMixin, viewsets.ModelViewSet):
    queryset = ParceiroFinanceiro.objects.all()
    serializer_class = ParceiroFinanceiroSerializer
    search_fields = ("nome", "documento", "email")


class CentroCustoViewSet(CadastroFinanceiroMixin, viewsets.ModelViewSet):
    queryset = CentroCusto.objects.select_related("propriedade").all()
    serializer_class = CentroCustoSerializer
    search_fields = ("nome", "safra", "propriedade__nome")


class LancamentoFinanceiroViewSet(viewsets.ModelViewSet):
    queryset = LancamentoFinanceiro.objects.select_related(
        "categoria",
        "parceiro",
        "centro_custo",
        "propriedade",
    )
    serializer_class = LancamentoFinanceiroSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ("descricao", "parceiro__nome", "observacoes", "safra")
    ordering_fields = ("data_vencimento", "valor", "descricao", "status", "tipo")
    ordering = ("data_vencimento", "id")

    def get_queryset(self):
        queryset = super().get_queryset()
        for parametro, campo in (
            ("tipo", "tipo"),
            ("status", "status"),
            ("categoria", "categoria_id"),
            ("parceiro", "parceiro_id"),
            ("centro_custo", "centro_custo_id"),
            ("propriedade", "propriedade_id"),
            ("safra", "safra"),
        ):
            valor = self.request.query_params.get(parametro, "").strip()
            if valor:
                queryset = queryset.filter(**{campo: valor})
        inicio = self.request.query_params.get("vencimento_inicio", "").strip()
        fim = self.request.query_params.get("vencimento_fim", "").strip()
        if inicio:
            queryset = queryset.filter(data_vencimento__gte=inicio)
        if fim:
            queryset = queryset.filter(data_vencimento__lte=fim)
        return queryset

    @action(detail=True, methods=["post"])
    def liquidar(self, request, pk=None):
        lancamento = self.get_object()
        try:
            data_liquidacao = date.fromisoformat(
                str(request.data.get("data_liquidacao", ""))
            )
            lancamento = liquidar_lancamento(
                lancamento,
                data_liquidacao=data_liquidacao,
                valor_liquidado=request.data.get("valor_liquidado"),
            )
        except (ValueError, OperacaoFinanceiraError) as exc:
            return Response(
                {"detail": str(exc) or "Dados de liquidação inválidos."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(self.get_serializer(lancamento).data)

    @action(detail=True, methods=["post"])
    def cancelar(self, request, pk=None):
        try:
            lancamento = cancelar_lancamento(self.get_object())
        except OperacaoFinanceiraError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(self.get_serializer(lancamento).data)

    @action(detail=False, methods=["get"])
    def resumo(self, request):
        return Response(resumo_financeiro(self.get_queryset()))

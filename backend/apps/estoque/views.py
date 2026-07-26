from django.db.models.deletion import ProtectedError
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    LocalEstoque,
    LoteEstoque,
    MovimentacaoEstoque,
    ProdutoEstoque,
)
from .serializers import (
    LocalEstoqueSerializer,
    LoteEstoqueSerializer,
    MovimentacaoEstoqueSerializer,
    ProdutoEstoqueSerializer,
)
from .services import posicao_estoque, resumo_estoque


class CadastroEstoqueMixin:
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    ordering = ("nome",)

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {"detail": "Este cadastro possui lotes ou movimentos vinculados."},
                status=status.HTTP_409_CONFLICT,
            )


class ProdutoEstoqueViewSet(CadastroEstoqueMixin, viewsets.ModelViewSet):
    queryset = ProdutoEstoque.objects.all()
    serializer_class = ProdutoEstoqueSerializer
    search_fields = ("nome", "fabricante")
    ordering_fields = ("nome", "categoria", "estoque_minimo", "criado_em")

    def get_queryset(self):
        queryset = super().get_queryset()
        categoria = self.request.query_params.get("categoria", "").strip()
        ativo = self.request.query_params.get("ativo", "").strip()
        if categoria:
            queryset = queryset.filter(categoria=categoria)
        if ativo in {"true", "false"}:
            queryset = queryset.filter(ativo=ativo == "true")
        return queryset


class LocalEstoqueViewSet(CadastroEstoqueMixin, viewsets.ModelViewSet):
    queryset = LocalEstoque.objects.select_related("propriedade")
    serializer_class = LocalEstoqueSerializer
    search_fields = ("nome", "descricao", "propriedade__nome")
    ordering_fields = ("nome", "criado_em")


class LoteEstoqueViewSet(CadastroEstoqueMixin, viewsets.ModelViewSet):
    queryset = LoteEstoque.objects.select_related("produto", "local")
    serializer_class = LoteEstoqueSerializer
    search_fields = ("codigo", "produto__nome", "local__nome")
    ordering_fields = ("codigo", "data_validade", "criado_em")
    ordering = ("data_validade", "codigo")

    def get_queryset(self):
        queryset = super().get_queryset()
        for parametro, campo in (
            ("produto", "produto_id"),
            ("local", "local_id"),
        ):
            valor = self.request.query_params.get(parametro, "").strip()
            if valor:
                queryset = queryset.filter(**{campo: valor})
        return queryset

    @action(detail=False, methods=["get"])
    def posicao(self, request):
        return Response(posicao_estoque(self.get_queryset()))

    @action(detail=False, methods=["get"])
    def resumo(self, request):
        return Response(resumo_estoque())


class MovimentacaoEstoqueViewSet(
    viewsets.mixins.CreateModelMixin,
    viewsets.mixins.ListModelMixin,
    viewsets.mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = MovimentacaoEstoque.objects.select_related(
        "lote__produto",
        "lote__local",
        "propriedade",
        "criado_por",
    )
    serializer_class = MovimentacaoEstoqueSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = (
        "lote__produto__nome",
        "lote__codigo",
        "documento_fiscal",
        "observacoes",
    )
    ordering = ("-data_movimento", "-id")
    ordering_fields = ("data_movimento", "quantidade", "custo_unitario", "tipo")

    def get_queryset(self):
        queryset = super().get_queryset()
        for parametro, campo in (
            ("tipo", "tipo"),
            ("lote", "lote_id"),
            ("produto", "lote__produto_id"),
            ("local", "lote__local_id"),
            ("propriedade", "propriedade_id"),
            ("safra", "safra"),
        ):
            valor = self.request.query_params.get(parametro, "").strip()
            if valor:
                queryset = queryset.filter(**{campo: valor})
        return queryset

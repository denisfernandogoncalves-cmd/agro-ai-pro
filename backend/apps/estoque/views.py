from django.db.models.deletion import ProtectedError
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.core.pagination import PaginacaoOpcional
from apps.core.query_params import validar_filtros

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
from .services import EstoqueInsuficienteError, excluir_movimentacao, posicao_estoque, resumo_estoque
from apps.core.correcoes import CorrecaoHistoricoMixin
from django.db import transaction
from decimal import Decimal
from rest_framework.exceptions import ValidationError


class CadastroEstoqueMixin:
    pagination_class = PaginacaoOpcional
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

    @action(detail=False, methods=["get"], url_path="consultar-adapar")
    def consultar_adapar(self, request):
        from .adapar import ConsultaIndisponivel, consultar
        nome = request.query_params.get("nome", "").strip()
        if not 3 <= len(nome) <= 160:
            return Response({"detail": "Informe de 3 a 160 caracteres do nome comercial."}, status=400)
        try:
            return Response(consultar(nome))
        except ConsultaIndisponivel as exc:
            return Response({"detail": str(exc)}, status=503)

    def get_queryset(self):
        validar_filtros(self.request.query_params, ids=('produto', 'local', 'fornecedor', 'lote', 'propriedade'))
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
    queryset = LoteEstoque.objects.select_related("produto", "local", "fornecedor")
    serializer_class = LoteEstoqueSerializer
    search_fields = ("codigo", "produto__nome", "local__nome", "fornecedor__nome")
    ordering_fields = ("codigo", "data_validade", "criado_em")
    ordering = ("data_validade", "codigo")

    def get_queryset(self):
        validar_filtros(self.request.query_params, ids=('produto', 'local', 'fornecedor', 'lote', 'propriedade'))
        queryset = super().get_queryset()
        for parametro, campo in (
            ("produto", "produto_id"),
            ("local", "local_id"),
            ("fornecedor", "fornecedor_id"),
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
    CorrecaoHistoricoMixin,
    viewsets.mixins.CreateModelMixin,
    viewsets.mixins.ListModelMixin,
    viewsets.mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    modulo_correcao = "estoque"
    campos_correcao = ("quantidade", "custo_unitario", "data_movimento", "documento_fiscal", "propriedade", "safra", "observacoes")

    def bloquear_dependencias(self, instancia):
        from .models import LoteEstoque
        LoteEstoque.objects.select_for_update().get(pk=instancia.lote_id)

    def corrigir_historico(self, instancia, dados, request):
        # Registros originados de compra/operação têm sua própria origem para correção.
        from .models import CompraEstoque, LoteEstoque
        from apps.producao.models import InsumoOperacao
        if CompraEstoque.objects.filter(movimento=instancia).exists() or InsumoOperacao.objects.filter(movimentacao_estoque=instancia).exists():
            raise ValidationError("Corrija este movimento pela compra ou operação de origem, para manter os vínculos consistentes.")
        lote = LoteEstoque.objects.select_for_update().get(pk=instancia.lote_id)
        for campo, valor in dados.items():
            setattr(instancia, campo, valor)
        instancia.full_clean()
        instancia.save()
        saldo = Decimal("0")
        for item in lote.movimentacoes.order_by("data_movimento", "id"):
            saldo += item.quantidade if item.tipo == "entrada" else -item.quantidade
            if saldo < 0:
                raise ValidationError("A correção deixaria o saldo negativo no histórico do lote. Nenhuma alteração foi salva.")

    def cancelar_historico(self, instancia, request):
        try:
            excluir_movimentacao(instancia)
            instancia.pk = None
        except (EstoqueInsuficienteError, ProtectedError) as exc:
            raise ValidationError("O cancelamento não pode ser realizado devido ao saldo ou vínculo da origem.") from exc
    queryset = MovimentacaoEstoque.objects.select_related(
        "lote__produto",
        "lote__local",
        "lote__fornecedor",
        "propriedade",
        "criado_por",
    )
    serializer_class = MovimentacaoEstoqueSerializer
    pagination_class = PaginacaoOpcional
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

    def destroy(self, request, *args, **kwargs):
        try:
            excluir_movimentacao(self.get_object())
        except EstoqueInsuficienteError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except ProtectedError:
            return Response({"detail": "Este lançamento está vinculado a uma operação agrícola e não pode ser excluído."}, status=status.HTTP_409_CONFLICT)
        except MovimentacaoEstoque.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_queryset(self):
        validar_filtros(self.request.query_params, ids=('produto', 'local', 'fornecedor', 'lote', 'propriedade'))
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

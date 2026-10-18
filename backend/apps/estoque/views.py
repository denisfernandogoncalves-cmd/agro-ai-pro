from django.http import HttpResponse
from django.utils import timezone
from django.template.loader import render_to_string
from rest_framework import serializers
from .models import CargaCavaco
from .serializers import CargaCavacoSerializer
from apps.accounts.access import verificar_acesso, pode
from rest_framework.exceptions import PermissionDenied
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
        if hasattr(instancia, "estorno_compra") or CompraEstoque.objects.filter(movimento=instancia).exists() or InsumoOperacao.objects.filter(movimentacao_estoque=instancia).exists():
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


class CargaCavacoViewSet(viewsets.ModelViewSet):
    queryset = CargaCavaco.objects.select_related('conta_pagar')
    serializer_class = CargaCavacoSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ('motorista', 'fornecedor', 'placa')
    ordering_fields = ('data', 'id', 'fornecedor')

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        verificar_acesso(request.user, request.path, request.method)
        if self.action == "romaneio" and not pode(request.user, "cavaco", "imprimir"):
            raise PermissionDenied("Seu usuário não pode imprimir romaneios de cavaco.")

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == 'list' and self.request.query_params.get('excluidas') == 'true':
            qs = qs.filter(excluido_em__isnull=False)
        else:
            qs = qs.filter(excluido_em__isnull=True)
        if self.action in ('update', 'partial_update', 'destroy'):
            qs = qs.select_for_update(of=('self',))
        # Detail actions remain available regardless of list filters.
        if self.action != 'list':
            return qs
        params = self.request.query_params
        inicio, fim = None, None
        for parametro, lookup in [('data_inicio', 'data__gte'), ('data_fim', 'data__lte')]:
            if params.get(parametro):
                valor = serializers.DateField().run_validation(params[parametro])
                qs = qs.filter(**{lookup: valor})
                if parametro == 'data_inicio':
                    inicio = valor
                else:
                    fim = valor
        if inicio and fim and inicio > fim:
            raise serializers.ValidationError({'data_fim': 'A data final deve ser igual ou posterior à inicial.'})
        if params.get('pago') in ('true', 'false'):
            qs = qs.filter(pago=params['pago'] == 'true')
        return qs

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        carga = self.get_object()
        carga.excluido_em = timezone.now()
        carga.save(update_fields=('excluido_em',))
        from .cavaco_financeiro import sincronizar_conta_cavaco
        sincronizar_conta_cavaco(carga)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'])
    def romaneio(self, request, pk=None):
        carga = self.get_object()
        html = render_to_string('estoque/romaneio_cavaco.html', {'carga': carga, 'vias': (1, 2)})
        response = HttpResponse(html, content_type='text/html; charset=utf-8')
        response['Cache-Control'] = 'no-store'
        return response

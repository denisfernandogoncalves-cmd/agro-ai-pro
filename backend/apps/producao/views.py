from apps.core.edicao_concorrente import EdicaoConcorrenteMixin
from datetime import date

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.core.pagination import PaginacaoOpcional
from apps.core.query_params import validar_filtros

from .models import InsumoOperacao, OperacaoAgricola
from apps.core.correcoes import CorrecaoHistoricoMixin
from rest_framework.exceptions import ValidationError
from .serializers import InsumoOperacaoSerializer, OperacaoAgricolaSerializer
from .services import (
    TransicaoOperacaoError,
    cancelar_operacao,
    concluir_operacao,
    iniciar_operacao,
)


class OperacaoAgricolaViewSet(CorrecaoHistoricoMixin, EdicaoConcorrenteMixin, viewsets.ModelViewSet):
    modulo_correcao = "operacoes"
    campos_correcao = ("talhao", "tipo", "descricao", "data_planejada", "area_hectares", "responsavel", "custo_estimado", "observacoes", "data_inicio", "data_conclusao", "custo_realizado", "area_realizada_hectares")

    def corrigir_historico(self, instancia, dados, request):
        if "talhao" in dados and dados["talhao"].pk != instancia.talhao_id and instancia.insumos.filter(movimentacao_estoque__isnull=False).exists():
            raise ValidationError("Cancele a operação antes de mudar o talhão, pois há consumo vinculado à propriedade original.")
        for campo, valor in dados.items():
            setattr(instancia, campo, valor)
        instancia.full_clean()
        instancia.save()

    def cancelar_historico(self, instancia, request):
        if instancia.status == "cancelada":
            raise ValidationError("A operação já está cancelada.")
        from apps.estoque.services import excluir_movimentacao
        for item in instancia.insumos.select_for_update(of=("self",)).select_related("movimentacao_estoque").order_by("lote_id", "id"):
            if item.movimentacao_estoque_id:
                movimento = item.movimentacao_estoque
                item.movimentacao_estoque = None
                item.quantidade_utilizada = None
                item.save(update_fields=["movimentacao_estoque", "quantidade_utilizada"])
                excluir_movimentacao(movimento)
        instancia.status = "cancelada"
        instancia.custo_realizado = None
        instancia.save(update_fields=["status", "custo_realizado", "atualizado_em"])
    queryset = OperacaoAgricola.objects.select_related(
        "talhao__propriedade", "criado_por"
    ).prefetch_related("insumos__lote__produto", "insumos__lote__local")
    serializer_class = OperacaoAgricolaSerializer
    pagination_class = PaginacaoOpcional
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ("descricao", "responsavel", "talhao__nome", "observacoes")
    ordering_fields = ("data_planejada", "tipo", "status", "custo_estimado")
    ordering = ("data_planejada", "id")

    def get_queryset(self):
        validar_filtros(self.request.query_params, ids=('talhao', 'propriedade', 'operacao', 'lote'))
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
                area_realizada_hectares=request.data.get("area_realizada_hectares"),
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


class InsumoOperacaoViewSet(CorrecaoHistoricoMixin, viewsets.ModelViewSet):
    modulo_correcao = "operacoes"
    campos_correcao = ("quantidade_planejada", "quantidade_utilizada")

    def bloquear_dependencias(self, instancia):
        from apps.estoque.models import LoteEstoque
        OperacaoAgricola.objects.select_for_update().get(pk=instancia.operacao_id)
        LoteEstoque.objects.select_for_update().get(pk=instancia.lote_id)

    def corrigir_historico(self, instancia, dados, request):
        from apps.estoque.models import LoteEstoque
        from decimal import Decimal
        lote = LoteEstoque.objects.select_for_update().get(pk=instancia.lote_id)
        for campo, valor in dados.items():
            setattr(instancia, campo, valor)
        instancia.clean_fields()
        if instancia.movimentacao_estoque_id:
            movimento = instancia.movimentacao_estoque
            movimento.quantidade = instancia.quantidade_utilizada or instancia.quantidade_planejada
            movimento.full_clean()
            movimento.save(update_fields=["quantidade"])
            saldo = Decimal("0")
            for item in lote.movimentacoes.order_by("data_movimento", "id"):
                saldo += item.quantidade if item.tipo == "entrada" else -item.quantidade
                if saldo < 0:
                    raise ValidationError("Quantidade corrigida excede o estoque disponível. Nenhuma alteração foi salva.")
            instancia.quantidade_utilizada = movimento.quantidade
        instancia.save()

    def cancelar_historico(self, instancia, request):
        from apps.estoque.services import excluir_movimentacao
        if instancia.movimentacao_estoque_id:
            movimento = instancia.movimentacao_estoque
            instancia.movimentacao_estoque = None
            instancia.save(update_fields=["movimentacao_estoque"])
            excluir_movimentacao(movimento)
        instancia.delete()
    queryset = InsumoOperacao.objects.select_related(
        "operacao", "lote__produto", "lote__local"
    )
    serializer_class = InsumoOperacaoSerializer
    pagination_class = PaginacaoOpcional
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ("lote__produto__nome", "lote__codigo", "operacao__descricao")
    ordering_fields = ("quantidade_planejada", "criado_em")

    def get_queryset(self):
        validar_filtros(self.request.query_params, ids=('talhao', 'propriedade', 'operacao', 'lote'))
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

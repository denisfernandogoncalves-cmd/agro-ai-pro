from django.core.exceptions import ValidationError
from django.db import IntegrityError
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.graos.services import SaldoGraosError

from .models import VendaGraos
from .selectors import selecionar_vendas
from .serializers import (
    CancelamentoSerializer,
    MovimentoVendaSerializer,
    VendaGraosCriacaoSerializer,
    VendaGraosSerializer,
)
from .services import (
    VendaGraosConflitoError,
    VendaGraosError,
    cancelar_venda,
    confirmar_venda,
    criar_rascunho,
    registrar_devolucao_venda,
    registrar_entrega_venda,
)


class VendaGraosViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = selecionar_vendas()
    serializer_class = VendaGraosSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ("numero_contrato", "cliente_nome", "observacoes")
    ordering_fields = ("data_contrato", "numero_contrato", "status", "quantidade_kg")
    ordering = ("-data_contrato", "-id")

    def get_queryset(self):
        queryset = selecionar_vendas()
        filtros = (
            ("status", "status"),
            ("cad_pro", "posicao__cad_pro_id"),
            ("safra", "posicao__safra"),
            ("armazem", "posicao__armazem_id"),
            ("propriedade", "posicao__armazem__propriedade_id"),
        )
        for parametro, campo in filtros:
            valor = self.request.query_params.get(parametro, "").strip()
            if valor:
                queryset = queryset.filter(**{campo: valor})
        for parametro, campo in (
            ("cultura", "posicao__cultura__iexact"),
            ("classificacao_codigo", "posicao__classificacao_codigo__iexact"),
        ):
            valor = self.request.query_params.get(parametro, "").strip()
            if valor:
                queryset = queryset.filter(**{campo: valor})
        return queryset

    def _chave(self, request):
        return request.headers.get("Idempotency-Key", "")

    def _erro(self, exc):
        codigo = getattr(exc, "codigo", "venda_invalida")
        http = (
            status.HTTP_409_CONFLICT
            if isinstance(exc, (VendaGraosConflitoError, SaldoGraosError))
            else status.HTTP_400_BAD_REQUEST
        )
        if isinstance(exc, ValidationError):
            detalhe = exc.message_dict if hasattr(exc, "message_dict") else exc.messages
        else:
            detalhe = str(exc)
        return Response({"detail": detalhe, "codigo": codigo}, status=http)

    def create(self, request, *args, **kwargs):
        entrada = VendaGraosCriacaoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        try:
            venda = criar_rascunho(
                usuario=request.user,
                chave_idempotencia=self._chave(request),
                **entrada.validated_data,
            )
        except (VendaGraosError, ValidationError, IntegrityError) as exc:
            return self._erro(exc)
        dados = VendaGraosSerializer(
            selecionar_vendas().get(pk=venda.pk), context=self.get_serializer_context()
        ).data
        return Response(dados, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def confirmar(self, request, pk=None):
        try:
            venda = confirmar_venda(
                usuario=request.user,
                venda=self.get_object(),
                chave_idempotencia=self._chave(request),
            )
            return Response(VendaGraosSerializer(selecionar_vendas().get(pk=venda.pk)).data)
        except (VendaGraosError, SaldoGraosError, ValidationError) as exc:
            return self._erro(exc)

    @action(detail=True, methods=["post"])
    def cancelar(self, request, pk=None):
        entrada = CancelamentoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        try:
            venda = cancelar_venda(
                usuario=request.user,
                venda=self.get_object(),
                chave_idempotencia=self._chave(request),
                **entrada.validated_data,
            )
            return Response(VendaGraosSerializer(selecionar_vendas().get(pk=venda.pk)).data)
        except (VendaGraosError, SaldoGraosError, ValidationError) as exc:
            return self._erro(exc)

    @action(detail=True, methods=["post"])
    def entregar(self, request, pk=None):
        entrada = MovimentoVendaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        dados = entrada.validated_data
        try:
            registrar_entrega_venda(
                usuario=request.user,
                venda=self.get_object(),
                chave_idempotencia=self._chave(request),
                data_entrega=dados.pop("data_movimento", None),
                **dados,
            )
            venda = selecionar_vendas().get(pk=pk)
            return Response(VendaGraosSerializer(venda).data, status=status.HTTP_201_CREATED)
        except (VendaGraosError, SaldoGraosError, ValidationError) as exc:
            return self._erro(exc)

    @action(detail=True, methods=["post"])
    def devolver(self, request, pk=None):
        entrada = MovimentoVendaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        dados = entrada.validated_data
        try:
            registrar_devolucao_venda(
                usuario=request.user,
                venda=self.get_object(),
                chave_idempotencia=self._chave(request),
                data_devolucao=dados.pop("data_movimento", None),
                **dados,
            )
            venda = selecionar_vendas().get(pk=pk)
            return Response(VendaGraosSerializer(venda).data, status=status.HTTP_201_CREATED)
        except (VendaGraosError, SaldoGraosError, ValidationError) as exc:
            return self._erro(exc)

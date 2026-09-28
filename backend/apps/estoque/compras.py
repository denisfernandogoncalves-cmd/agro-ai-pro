import hashlib
import json
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from rest_framework import serializers, status, viewsets
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import filters
from rest_framework.decorators import action

from apps.financeiro.models import ParceiroFinanceiro
from .compras_calculos import calcular_compra
from .models import CompraEstoque, LoteEstoque, MovimentacaoEstoque, ProdutoEstoque
from .services import EstoqueInsuficienteError, excluir_movimentacao, registrar_movimentacao


class CompraConflitante(APIException):
    status_code = 409
    default_detail = "Esta solicitação já foi registrada com outros dados. Confira a lista de compras."


class CompraEntradaSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    data_compra = serializers.DateField()
    produto = serializers.PrimaryKeyRelatedField(queryset=ProdutoEstoque.objects.filter(ativo=True, unidade__in=["l", "kg"]))
    cultura = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    safra = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")
    quantidade_embalagens = serializers.DecimalField(max_digits=14, decimal_places=3, min_value=Decimal("0.001"))
    embalagem = serializers.CharField(max_length=20)
    conteudo_embalagem = serializers.DecimalField(max_digits=14, decimal_places=3, min_value=Decimal("0.001"))
    fornecedor = serializers.PrimaryKeyRelatedField(queryset=ParceiroFinanceiro.objects.filter(ativo=True, tipo__in=["fornecedor", "ambos"]))
    custo_embalagem = serializers.DecimalField(max_digits=14, decimal_places=4, min_value=Decimal("0"))
    data_vencimento = serializers.DateField(required=False, allow_null=True, default=None)

    def validate(self, attrs):
        try:
            calcular_compra(attrs["quantidade_embalagens"], attrs["conteudo_embalagem"], attrs["custo_embalagem"])
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc
        return attrs


class CompraSerializer(serializers.ModelSerializer):
    situacao = serializers.SerializerMethodField()
    safra = serializers.CharField(source="movimento.safra", read_only=True)
    data_compra = serializers.DateField(source="movimento.data_movimento", read_only=True)
    produto_nome = serializers.CharField(source="movimento.lote.produto.nome", read_only=True)
    unidade = serializers.CharField(source="movimento.lote.produto.unidade", read_only=True)
    fornecedor_nome = serializers.CharField(source="movimento.lote.fornecedor.nome", read_only=True)
    quantidade_total = serializers.DecimalField(source="movimento.quantidade", max_digits=14, decimal_places=3, read_only=True)
    valor_por_unidade = serializers.DecimalField(source="movimento.custo_unitario", max_digits=14, decimal_places=4, read_only=True)

    class Meta:
        model = CompraEstoque
        exclude = ("assinatura",)

    def get_situacao(self, obj):
        return "pago" if obj.data_pagamento else "pendente"


def registrar_compra(*, usuario, dados):
    campos = dict(dados)
    chave = campos.pop("id")
    canonico = {k: str(v.pk) if hasattr(v, "pk") else str(v) for k, v in campos.items()}
    # Mantém a assinatura das compras anteriores à inclusão de safra.
    if not canonico.get("safra"):
        canonico.pop("safra", None)
    assinatura = hashlib.sha256(json.dumps(canonico, sort_keys=True).encode()).hexdigest()

    def repetir(compra):
        if compra.assinatura != assinatura:
            raise CompraConflitante()
        return compra, True

    existente = CompraEstoque.objects.filter(pk=chave).first()
    if existente:
        return repetir(existente)
    try:
        with transaction.atomic():
            # Serializa compras do mesmo produto e revalida o cadastro no momento da gravação.
            produto = ProdutoEstoque.objects.select_for_update().get(pk=campos.pop("produto").pk)
            fornecedor = ParceiroFinanceiro.objects.select_for_update().get(pk=campos.pop("fornecedor").pk)
            existente = CompraEstoque.objects.filter(pk=chave).first()
            if existente:
                return repetir(existente)
            if LoteEstoque.objects.filter(codigo=f"COMPRA-{chave}").exists():
                raise CompraConflitante("Esta compra foi excluída. Inicie um novo lançamento para registrar outra compra.")
            if not produto.ativo or produto.unidade not in {"l", "kg"} or not fornecedor.ativo or fornecedor.tipo not in {"fornecedor", "ambos"}:
                raise serializers.ValidationError("Selecione produto em litros/kg e fornecedor ativos.")
            calculo = calcular_compra(campos["quantidade_embalagens"], campos["conteudo_embalagem"], campos["custo_embalagem"])
            lote = LoteEstoque.objects.create(produto=produto, fornecedor=fornecedor, codigo=f"COMPRA-{chave}")
            movimento = registrar_movimentacao(usuario=usuario, lote=lote, tipo="entrada", quantidade=calculo["quantidade"], custo_unitario=calculo["custo_unitario"], data_movimento=campos.pop("data_compra"), safra=campos.pop("safra", ""))
            compra = CompraEstoque(id=chave, assinatura=assinatura, movimento=movimento, valor_total=calculo["valor_total"], **campos)
            compra.full_clean()
            compra.save(force_insert=True)
            return compra, False
    except IntegrityError:
        existente = CompraEstoque.objects.filter(pk=chave).first()
        if existente:
            return repetir(existente)
        raise


class CompraEstoqueViewSet(viewsets.mixins.ListModelMixin, viewsets.mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CompraSerializer
    queryset = CompraEstoque.objects.select_related("movimento__lote__produto", "movimento__lote__fornecedor")
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ("movimento__lote__produto__nome", "cultura", "movimento__safra", "movimento__lote__fornecedor__nome")
    ordering_fields = ("movimento__data_movimento", "data_vencimento", "valor_total")

    def get_queryset(self):
        entrada = FiltrosComprasSerializer(data={k: v for k, v in self.request.query_params.items() if v})
        entrada.is_valid(raise_exception=True)
        filtros = entrada.validated_data
        queryset = super().get_queryset()
        if filtros.get("fornecedor"):
            queryset = queryset.filter(movimento__lote__fornecedor_id=filtros["fornecedor"])
        if filtros.get("situacao"):
            queryset = queryset.filter(data_pagamento__isnull=filtros["situacao"] == "pendente")
        campo = {"vencimento": "data_vencimento", "compra": "movimento__data_movimento", "pagamento": "data_pagamento"}[filtros["data_referencia"]]
        for limite, operador in (("data_inicio", "gte"), ("data_fim", "lte")):
            if filtros.get(limite):
                queryset = queryset.filter(**{f"{campo}__{operador}": filtros[limite]})
        return queryset

    @action(detail=True, methods=["post"])
    def pagar(self, request, pk=None):
        compra = self.get_object()
        entrada = PagamentoCompraSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        with transaction.atomic():
            LoteEstoque.objects.select_for_update().get(pk=compra.movimento.lote_id)
            compra = CompraEstoque.objects.select_for_update().filter(pk=compra.pk).first()
            if compra is None:
                return Response(status=status.HTTP_404_NOT_FOUND)
            if compra.data_pagamento:
                return Response({"detail": "Esta compra já foi marcada como paga."}, status=status.HTTP_409_CONFLICT)
            compra.data_pagamento = entrada.validated_data["data_pagamento"]
            compra.valor_pago = entrada.validated_data["valor_pago"]
            compra.save(update_fields=("data_pagamento", "valor_pago"))
        return Response(self.get_serializer(compra).data)

    def destroy(self, request, *args, **kwargs):
        compra = self.get_object()
        try:
            excluir_movimentacao(compra.movimento)
        except EstoqueInsuficienteError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except ProtectedError:
            return Response({"detail": "A entrada desta compra está vinculada a uma operação agrícola e não pode ser excluída."}, status=status.HTTP_409_CONFLICT)
        except MovimentacaoEstoque.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def create(self, request):
        entrada = CompraEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        compra, replay = registrar_compra(usuario=request.user, dados=entrada.validated_data)
        return Response(self.get_serializer(compra).data, status=status.HTTP_200_OK if replay else status.HTTP_201_CREATED)


class FiltrosComprasSerializer(serializers.Serializer):
    fornecedor = serializers.IntegerField(min_value=1, required=False)
    situacao = serializers.ChoiceField(choices=("pendente", "pago"), required=False)
    data_referencia = serializers.ChoiceField(choices=("vencimento", "compra", "pagamento"), default="vencimento")
    data_inicio = serializers.DateField(required=False)
    data_fim = serializers.DateField(required=False)

    def validate(self, attrs):
        if attrs.get("data_inicio") and attrs.get("data_fim") and attrs["data_inicio"] > attrs["data_fim"]:
            raise serializers.ValidationError("A data final deve ser igual ou posterior à inicial.")
        return attrs


class PagamentoCompraSerializer(serializers.Serializer):
    data_pagamento = serializers.DateField()
    valor_pago = serializers.DecimalField(max_digits=24, decimal_places=2, min_value=Decimal("0"))

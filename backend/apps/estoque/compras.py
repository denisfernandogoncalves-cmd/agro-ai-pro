import hashlib
import json
from decimal import Decimal

from django.db import IntegrityError, transaction
from rest_framework import serializers, status, viewsets
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import filters

from apps.financeiro.models import ParceiroFinanceiro
from .compras_calculos import calcular_compra
from .models import CompraEstoque, LoteEstoque, ProdutoEstoque
from .services import registrar_movimentacao


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

    def create(self, request):
        entrada = CompraEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        compra, replay = registrar_compra(usuario=request.user, dados=entrada.validated_data)
        return Response(self.get_serializer(compra).data, status=status.HTTP_200_OK if replay else status.HTTP_201_CREATED)

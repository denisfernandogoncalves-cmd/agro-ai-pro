from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import (
    LocalEstoque,
    LoteEstoque,
    MovimentacaoEstoque,
    ProdutoEstoque,
)
from .services import EstoqueInsuficienteError, registrar_movimentacao, saldo_lote


class ProdutoEstoqueSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProdutoEstoque
        fields = "__all__"
        read_only_fields = ("criado_em",)
        extra_kwargs = {
            "fabricante": {
                "required": False,
                "allow_blank": True,
                "default": "",
            }
        }


class LocalEstoqueSerializer(serializers.ModelSerializer):
    propriedade_nome = serializers.CharField(
        source="propriedade.nome", read_only=True
    )

    class Meta:
        model = LocalEstoque
        fields = "__all__"
        read_only_fields = ("criado_em",)


class LoteEstoqueSerializer(serializers.ModelSerializer):
    produto_nome = serializers.CharField(source="produto.nome", read_only=True)
    produto_unidade = serializers.CharField(source="produto.unidade", read_only=True)
    local_nome = serializers.CharField(source="local.nome", read_only=True)
    saldo = serializers.SerializerMethodField()
    vencido = serializers.BooleanField(read_only=True)

    class Meta:
        model = LoteEstoque
        fields = "__all__"
        read_only_fields = ("criado_em",)

    def get_saldo(self, obj):
        return saldo_lote(obj)


class MovimentacaoEstoqueSerializer(serializers.ModelSerializer):
    produto_nome = serializers.CharField(source="lote.produto.nome", read_only=True)
    unidade = serializers.CharField(source="lote.produto.unidade", read_only=True)
    lote_codigo = serializers.CharField(source="lote.codigo", read_only=True)
    local_nome = serializers.CharField(source="lote.local.nome", read_only=True)
    propriedade_nome = serializers.CharField(
        source="propriedade.nome", read_only=True
    )
    criado_por_nome = serializers.CharField(
        source="criado_por.username", read_only=True
    )

    class Meta:
        model = MovimentacaoEstoque
        fields = "__all__"
        read_only_fields = ("criado_por", "criado_em")

    def create(self, validated_data):
        try:
            return registrar_movimentacao(
                usuario=self.context["request"].user,
                **validated_data,
            )
        except (ValueError, EstoqueInsuficienteError, DjangoValidationError) as exc:
            if isinstance(exc, DjangoValidationError):
                detalhe = exc.message_dict
            else:
                detalhe = {"detail": str(exc)}
            raise serializers.ValidationError(detalhe) from exc

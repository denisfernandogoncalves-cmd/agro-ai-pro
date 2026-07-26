from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import serializers

from .models import (
    CategoriaFinanceira,
    CentroCusto,
    LancamentoFinanceiro,
    ParceiroFinanceiro,
)


class CategoriaFinanceiraSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoriaFinanceira
        fields = "__all__"
        read_only_fields = ("criado_em",)


class ParceiroFinanceiroSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParceiroFinanceiro
        fields = "__all__"
        read_only_fields = ("criado_em",)


class CentroCustoSerializer(serializers.ModelSerializer):
    propriedade_nome = serializers.CharField(
        source="propriedade.nome",
        read_only=True,
    )

    class Meta:
        model = CentroCusto
        fields = "__all__"
        read_only_fields = ("criado_em",)


class LancamentoFinanceiroSerializer(serializers.ModelSerializer):
    categoria_nome = serializers.CharField(source="categoria.nome", read_only=True)
    parceiro_nome = serializers.CharField(source="parceiro.nome", read_only=True)
    centro_custo_nome = serializers.CharField(
        source="centro_custo.nome",
        read_only=True,
    )
    propriedade_nome = serializers.CharField(
        source="propriedade.nome",
        read_only=True,
    )
    atrasado = serializers.BooleanField(read_only=True)

    class Meta:
        model = LancamentoFinanceiro
        fields = "__all__"
        read_only_fields = (
            "status",
            "data_liquidacao",
            "valor_liquidado",
            "criado_em",
            "atualizado_em",
        )

    def validate_data_vencimento(self, value):
        if not self.instance and value < timezone.localdate().replace(year=timezone.localdate().year - 10):
            raise serializers.ValidationError("A data de vencimento é muito antiga.")
        return value

    def validate(self, attrs):
        instancia = self.instance or LancamentoFinanceiro()
        for campo, valor in attrs.items():
            setattr(instancia, campo, valor)
        try:
            instancia.clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc
        return attrs

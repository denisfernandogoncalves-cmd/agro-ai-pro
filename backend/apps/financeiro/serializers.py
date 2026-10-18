from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import serializers
from .codigos import CodigoPagamentoInvalido, ler_codigo_pagamento

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
    codigo_barras = serializers.CharField(max_length=100, required=False, allow_blank=True)
    categoria_nome = serializers.CharField(source="categoria.nome", read_only=True, allow_null=True)
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
            "parcelamento",
            "parcela_numero",
            "status",
            "data_liquidacao",
            "valor_liquidado",
            "criado_em",
            "atualizado_em",
        )

    def validate_data_vencimento(self, value):
        hoje = timezone.localdate()
        try:
            limite = hoje.replace(year=hoje.year - 10)
        except ValueError:
            limite = hoje.replace(year=hoje.year - 10, day=28)
        if not self.instance and value < limite:
            raise serializers.ValidationError("A data de vencimento é muito antiga.")
        return value

    def validate_codigo_barras(self, value):
        if not value:
            return ""
        try:
            return ler_codigo_pagamento(value)["codigo_barras"]
        except CodigoPagamentoInvalido as exc:
            raise serializers.ValidationError(str(exc)) from exc

    def validate(self, attrs):
        instancia = self.instance or LancamentoFinanceiro()
        origens_novas = ('transportes_lancamentotransporte_origem', 'transportes_remuneracaomotorista_origem', 'maquinas_manutencaomaquina_origem')
        if self.instance and any(hasattr(instancia, nome) for nome in origens_novas):
            protegidos = ('tipo', 'descricao', 'valor', 'data_emissao', 'recebedor_nome', 'propriedade')
            if any(k in attrs and attrs[k] != getattr(instancia, k) for k in protegidos):
                raise serializers.ValidationError('Corrija os valores na origem. Confira o vencimento e a baixa no Financeiro.')
        if self.instance and (hasattr(instancia, 'compra_diesel_origem') or hasattr(instancia, 'carga_cavaco_origem') or hasattr(instancia, 'compra_estoque_origem') or hasattr(instancia, 'estorno_compra_origem')):
            protegidos = ('tipo', 'descricao', 'valor', 'data_emissao', 'data_vencimento', 'recebedor_nome', 'parceiro', 'safra')
            if any(k in attrs and attrs[k] != getattr(instancia, k) for k in protegidos):
                raise serializers.ValidationError('Edite os dados e o vencimento na compra ou carga de origem. A liquidação permanece no Financeiro.')
        for campo, valor in attrs.items():
            setattr(instancia, campo, valor)
        try:
            instancia.clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc
        return attrs

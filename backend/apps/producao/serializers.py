from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import InsumoOperacao, OperacaoAgricola


class InsumoOperacaoSerializer(serializers.ModelSerializer):
    produto_nome = serializers.CharField(source="lote.produto.nome", read_only=True)
    lote_codigo = serializers.CharField(source="lote.codigo", read_only=True)
    unidade = serializers.CharField(source="lote.produto.unidade", read_only=True)
    local_nome = serializers.CharField(source="lote.local.nome", read_only=True)

    class Meta:
        model = InsumoOperacao
        fields = "__all__"
        read_only_fields = ("movimentacao_estoque", "criado_em")

    def validate(self, attrs):
        instancia = self.instance or InsumoOperacao()
        for campo, valor in attrs.items():
            setattr(instancia, campo, valor)
        try:
            instancia.clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc
        return attrs


class OperacaoAgricolaSerializer(serializers.ModelSerializer):
    talhao_nome = serializers.CharField(source="talhao.nome", read_only=True)
    propriedade_id = serializers.IntegerField(
        source="talhao.propriedade_id", read_only=True
    )
    propriedade_nome = serializers.CharField(
        source="talhao.propriedade.nome", read_only=True
    )
    criado_por_nome = serializers.CharField(
        source="criado_por.username", read_only=True
    )
    insumos = InsumoOperacaoSerializer(many=True, read_only=True)

    class Meta:
        model = OperacaoAgricola
        fields = "__all__"
        read_only_fields = (
            "status",
            "data_inicio",
            "data_conclusao",
            "custo_realizado",
            "criado_por",
            "criado_em",
            "atualizado_em",
        )

    def validate(self, attrs):
        instancia = self.instance or OperacaoAgricola(
            criado_por=self.context["request"].user
        )
        for campo, valor in attrs.items():
            setattr(instancia, campo, valor)
        try:
            instancia.clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc
        return attrs

    def create(self, validated_data):
        return OperacaoAgricola.objects.create(
            criado_por=self.context["request"].user,
            **validated_data,
        )

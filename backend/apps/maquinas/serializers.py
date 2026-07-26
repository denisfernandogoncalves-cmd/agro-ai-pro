from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from .models import (
    AbastecimentoMaquina,
    Maquina,
    ManutencaoMaquina,
    UsoMaquina,
)
from .services import HorimetroInvalidoError, atualizar_horimetro


class MaquinaSerializer(serializers.ModelSerializer):
    propriedade_nome = serializers.CharField(
        source="propriedade.nome", read_only=True
    )

    class Meta:
        model = Maquina
        fields = "__all__"
        read_only_fields = ("criado_em", "atualizado_em")

    def validate_horimetro_atual(self, value):
        if self.instance and value < self.instance.horimetro_atual:
            raise serializers.ValidationError("O horímetro não pode regredir.")
        return value


class UsoMaquinaSerializer(serializers.ModelSerializer):
    maquina_nome = serializers.CharField(source="maquina.identificacao", read_only=True)
    operacao_nome = serializers.CharField(source="operacao.descricao", read_only=True)
    horas_trabalhadas = serializers.DecimalField(
        max_digits=12, decimal_places=1, read_only=True
    )

    class Meta:
        model = UsoMaquina
        fields = "__all__"
        read_only_fields = ("criado_em",)

    @transaction.atomic
    def create(self, validated_data):
        instancia = UsoMaquina(**validated_data)
        try:
            if instancia.horimetro_inicial < instancia.maquina.horimetro_atual:
                raise HorimetroInvalidoError(
                    "O horímetro inicial não pode ser menor que o atual."
                )
            instancia.full_clean()
            atualizar_horimetro(instancia.maquina, instancia.horimetro_final)
        except (DjangoValidationError, HorimetroInvalidoError) as exc:
            raise serializers.ValidationError(str(exc)) from exc
        instancia.save()
        return instancia


class AbastecimentoMaquinaSerializer(serializers.ModelSerializer):
    maquina_nome = serializers.CharField(source="maquina.identificacao", read_only=True)

    class Meta:
        model = AbastecimentoMaquina
        fields = "__all__"
        read_only_fields = ("criado_em",)

    @transaction.atomic
    def create(self, validated_data):
        try:
            atualizar_horimetro(validated_data["maquina"], validated_data["horimetro"])
        except HorimetroInvalidoError as exc:
            raise serializers.ValidationError({"horimetro": str(exc)}) from exc
        return super().create(validated_data)


class ManutencaoMaquinaSerializer(serializers.ModelSerializer):
    maquina_nome = serializers.CharField(source="maquina.identificacao", read_only=True)

    class Meta:
        model = ManutencaoMaquina
        fields = "__all__"
        read_only_fields = (
            "status",
            "data_conclusao",
            "horimetro_realizado",
            "custo",
            "criado_em",
        )

from rest_framework import serializers

from .models import (
    AlertaClimatico,
    AtualizacaoClima,
    ConfiguracaoClima,
    PrevisaoClima,
    PrevisaoHoraria,
)


class PrevisaoClimaSerializer(serializers.ModelSerializer):
    propriedade_nome = serializers.CharField(source="propriedade.nome", read_only=True)

    class Meta:
        model = PrevisaoClima
        fields = "__all__"
        read_only_fields = tuple(campo.name for campo in PrevisaoClima._meta.fields)


class PrevisaoHorariaSerializer(serializers.ModelSerializer):
    propriedade_nome = serializers.CharField(source="propriedade.nome", read_only=True)

    class Meta:
        model = PrevisaoHoraria
        fields = "__all__"
        read_only_fields = tuple(campo.name for campo in PrevisaoHoraria._meta.fields)


class AlertaClimaticoSerializer(serializers.ModelSerializer):
    propriedade_nome = serializers.CharField(source="propriedade.nome", read_only=True)
    talhao_nome = serializers.CharField(source="talhao.nome", read_only=True)

    class Meta:
        model = AlertaClimatico
        fields = "__all__"
        read_only_fields = tuple(campo.name for campo in AlertaClimatico._meta.fields)


class AtualizacaoClimaSerializer(serializers.ModelSerializer):
    propriedade_nome = serializers.CharField(source="propriedade.nome", read_only=True)

    class Meta:
        model = AtualizacaoClima
        fields = "__all__"
        read_only_fields = tuple(campo.name for campo in AtualizacaoClima._meta.fields)


class ConfiguracaoClimaSerializer(serializers.ModelSerializer):
    propriedade_nome = serializers.CharField(source="propriedade.nome", read_only=True)
    desatualizado = serializers.BooleanField(read_only=True)

    class Meta:
        model = ConfiguracaoClima
        fields = "__all__"
        read_only_fields = (
            "propriedade",
            "ultima_tentativa",
            "ultima_atualizacao",
            "proxima_atualizacao",
            "status",
            "erro_ultima_atualizacao",
            "falhas_consecutivas",
            "total_chamadas",
            "origem_coordenadas",
            "latitude_usada",
            "longitude_usada",
            "altitude_usada",
            "dados_atuais",
            "atualizado_em",
        )

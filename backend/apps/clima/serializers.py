from rest_framework import serializers

from .models import PrevisaoClima


class PrevisaoClimaSerializer(serializers.ModelSerializer):
    propriedade_nome = serializers.CharField(
        source="propriedade.nome",
        read_only=True,
    )

    class Meta:
        model = PrevisaoClima
        fields = "__all__"
        read_only_fields = (
            "propriedade",
            "data",
            "temperatura_min",
            "temperatura_max",
            "chuva_mm",
            "umidade",
            "vento_kmh",
            "condicao",
            "probabilidade_chuva",
            "codigo_tempo",
            "alerta_agricola",
            "fonte",
            "criado_em",
            "atualizado_em",
        )

from rest_framework import serializers
from .models import PrevisaoClima


class PrevisaoClimaSerializer(serializers.ModelSerializer):

    propriedade_nome = serializers.CharField(
        source="propriedade.nome",
        read_only=True
    )

    class Meta:
        model = PrevisaoClima
        fields = "__all__"
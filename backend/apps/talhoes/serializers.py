from rest_framework import serializers
from .models import Talhao


class TalhaoSerializer(serializers.ModelSerializer):

    propriedade_nome = serializers.CharField(
        source="propriedade.nome",
        read_only=True
    )

    class Meta:
        model = Talhao
        fields = "__all__"
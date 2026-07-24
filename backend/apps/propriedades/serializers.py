from rest_framework import serializers

from .models import Propriedade
from .services import atualizar_coordenadas_kml


class PropriedadeSerializer(serializers.ModelSerializer):

    class Meta:
        model = Propriedade
        fields = "__all__"


    def create(self, validated_data):

        propriedade = Propriedade.objects.create(
            **validated_data
        )

        if propriedade.arquivo_kml:
            atualizar_coordenadas_kml(propriedade)

        return propriedade


    def update(self, instance, validated_data):

        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)

        instance.save()

        if instance.arquivo_kml:
            atualizar_coordenadas_kml(instance)

        return instance
from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from .models import HistoricoAgronomico, Talhao
from .services import processar_kml


class TalhaoSerializer(serializers.ModelSerializer):

    propriedade_nome = serializers.CharField(
        source="propriedade.nome",
        read_only=True
    )

    class Meta:
        model = Talhao
        fields = "__all__"
        read_only_fields = ("geometria_geojson", "latitude_centro", "longitude_centro")

    def validate(self, attrs):
        instancia = self.instance or Talhao()
        for campo, valor in attrs.items():
            setattr(instancia, campo, valor)
        try:
            instancia.clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from None
        arquivo = attrs.get("arquivo_kml")
        if arquivo:
            try:
                attrs.update(processar_kml(arquivo))
            except DjangoValidationError as exc:
                raise serializers.ValidationError({"arquivo_kml": exc.messages}) from None
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        return super().create(validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):
        return super().update(instance, validated_data)


class HistoricoAgronomicoSerializer(serializers.ModelSerializer):
    talhao_nome = serializers.CharField(source="talhao.nome", read_only=True)

    class Meta:
        model = HistoricoAgronomico
        fields = "__all__"

    def validate(self, attrs):
        instancia = self.instance or HistoricoAgronomico()
        for campo, valor in attrs.items():
            setattr(instancia, campo, valor)
        try:
            instancia.clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from None
        return attrs

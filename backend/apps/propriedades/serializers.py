from rest_framework import serializers

from .kml_service import KMLInvalidoError, extrair_centroide_kml
from .models import Propriedade
from .services import atualizar_coordenadas_kml


class PropriedadeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Propriedade
        fields = "__all__"

    def validate_area_hectares(self, value):
        if value <= 0:
            raise serializers.ValidationError("A área deve ser maior que zero.")
        return value

    def validate_uf(self, value):
        valor = value.strip().upper()
        if valor and (len(valor) != 2 or not valor.isalpha()):
            raise serializers.ValidationError("Informe a UF com duas letras.")
        return valor

    def validate_arquivo_kml(self, value):
        if not value:
            return value
        if not value.name.lower().endswith(".kml"):
            raise serializers.ValidationError("Envie um arquivo com extensão .kml.")
        try:
            extrair_centroide_kml(value)
        except (KMLInvalidoError, OSError) as exc:
            raise serializers.ValidationError(str(exc)) from exc
        return value

    def validate(self, attrs):
        latitude = attrs.get("latitude", getattr(self.instance, "latitude", None))
        longitude = attrs.get("longitude", getattr(self.instance, "longitude", None))
        if (latitude is None) != (longitude is None):
            raise serializers.ValidationError(
                "Latitude e longitude devem ser informadas em conjunto."
            )
        if latitude is not None and not -90 <= latitude <= 90:
            raise serializers.ValidationError({"latitude": "Informe um valor entre -90 e 90."})
        if longitude is not None and not -180 <= longitude <= 180:
            raise serializers.ValidationError(
                {"longitude": "Informe um valor entre -180 e 180."}
            )
        return attrs

    def create(self, validated_data):
        propriedade = Propriedade.objects.create(**validated_data)
        if propriedade.arquivo_kml:
            atualizar_coordenadas_kml(propriedade)
        return propriedade

    def update(self, instance, validated_data):
        novo_kml = "arquivo_kml" in validated_data and validated_data["arquivo_kml"]
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        instance.save()
        if novo_kml:
            atualizar_coordenadas_kml(instance)
        return instance

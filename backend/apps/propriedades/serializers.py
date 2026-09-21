from django.db import transaction
from rest_framework import serializers

from .kml_service import KMLInvalidoError, extrair_centroide_kml
from .models import Propriedade
from .services import atualizar_coordenadas_kml
from apps.talhoes.services import comparar_areas
from apps.cadpro.services import (
    NumeroCADProInvalido,
    vincular_numero_cadpro_a_propriedade,
)


class PropriedadeSerializer(serializers.ModelSerializer):
    diferenca_area_hectares = serializers.SerializerMethodField()
    divergencia_area_percentual = serializers.SerializerMethodField()
    cad_pro_numero = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        max_length=50,
    )
    cad_pro_numeros = serializers.SerializerMethodField()

    class Meta:
        model = Propriedade
        fields = "__all__"
        read_only_fields = (
            "geometria_geojson",
            "area_calculada_hectares",
            "diferenca_area_hectares",
            "divergencia_area_percentual",
            "cad_pro_numeros",
        )

    def _comparacao(self, obj):
        return comparar_areas(obj.area_hectares, obj.area_calculada_hectares)

    def get_diferenca_area_hectares(self, obj):
        return self._comparacao(obj)["diferenca_hectares"]

    def get_divergencia_area_percentual(self, obj):
        return self._comparacao(obj)["divergencia_percentual"]

    def get_cad_pro_numeros(self, obj):
        return [
            vinculo.cad_pro.codigo
            for vinculo in obj.vinculos_cadpro.all()
            if vinculo.ativo and vinculo.cad_pro.ativo
        ]

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

    @transaction.atomic
    def create(self, validated_data):
        cad_pro_numero = validated_data.pop("cad_pro_numero", "")
        propriedade = Propriedade.objects.create(**validated_data)
        if cad_pro_numero:
            try:
                vincular_numero_cadpro_a_propriedade(
                    numero=cad_pro_numero,
                    propriedade=propriedade,
                )
            except NumeroCADProInvalido as exc:
                raise serializers.ValidationError(
                    {"cad_pro_numero": str(exc)}
                ) from exc
        if propriedade.arquivo_kml:
            atualizar_coordenadas_kml(propriedade)
        return propriedade

    @transaction.atomic
    def update(self, instance, validated_data):
        cad_pro_numero = validated_data.pop("cad_pro_numero", "")
        novo_kml = "arquivo_kml" in validated_data and validated_data["arquivo_kml"]
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        instance.save()
        if cad_pro_numero:
            try:
                vincular_numero_cadpro_a_propriedade(
                    numero=cad_pro_numero,
                    propriedade=instance,
                )
            except NumeroCADProInvalido as exc:
                raise serializers.ValidationError(
                    {"cad_pro_numero": str(exc)}
                ) from exc
        if novo_kml:
            atualizar_coordenadas_kml(instance)
        return instance

from rest_framework import serializers

from apps.core.access import (
    PAPEL_ADMINISTRADOR,
    PAPEL_GESTOR,
    PAPEL_OPERADOR,
    papel_na_propriedade,
)
from apps.talhoes.services import comparar_areas

from .kml_service import KMLInvalidoError, extrair_centroide_kml
from .models import AcessoPropriedade, Propriedade
from .services import atualizar_coordenadas_kml


class PropriedadeSerializer(serializers.ModelSerializer):
    diferenca_area_hectares = serializers.SerializerMethodField()
    divergencia_area_percentual = serializers.SerializerMethodField()
    papel_usuario = serializers.SerializerMethodField()
    pode_editar = serializers.SerializerMethodField()
    pode_excluir = serializers.SerializerMethodField()
    pode_operar = serializers.SerializerMethodField()

    class Meta:
        model = Propriedade
        fields = "__all__"
        read_only_fields = (
            "geometria_geojson",
            "area_calculada_hectares",
            "diferenca_area_hectares",
            "divergencia_area_percentual",
            "papel_usuario",
            "pode_editar",
            "pode_excluir",
            "pode_operar",
        )

    def _comparacao(self, obj):
        return comparar_areas(obj.area_hectares, obj.area_calculada_hectares)

    def _papel(self, obj):
        request = self.context.get("request")
        return papel_na_propriedade(request.user, obj) if request else None

    def get_diferenca_area_hectares(self, obj):
        return self._comparacao(obj)["diferenca_hectares"]

    def get_divergencia_area_percentual(self, obj):
        return self._comparacao(obj)["divergencia_percentual"]

    def get_papel_usuario(self, obj):
        return self._papel(obj)

    def get_pode_editar(self, obj):
        return self._papel(obj) in {PAPEL_ADMINISTRADOR, PAPEL_GESTOR}

    def get_pode_excluir(self, obj):
        return self._papel(obj) == PAPEL_ADMINISTRADOR

    def get_pode_operar(self, obj):
        return self._papel(obj) in {
            PAPEL_ADMINISTRADOR,
            PAPEL_GESTOR,
            PAPEL_OPERADOR,
        }

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
            raise serializers.ValidationError(
                {"latitude": "Informe um valor entre -90 e 90."}
            )
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


class AcessoPropriedadeSerializer(serializers.ModelSerializer):
    usuario_nome = serializers.CharField(source="usuario.username", read_only=True)
    propriedade_nome = serializers.CharField(
        source="propriedade.nome",
        read_only=True,
    )

    class Meta:
        model = AcessoPropriedade
        fields = "__all__"
        read_only_fields = ("criado_em", "atualizado_em")

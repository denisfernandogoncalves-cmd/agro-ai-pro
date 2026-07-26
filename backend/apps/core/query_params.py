from rest_framework import serializers


class FiltrosPropriedadeSafraSerializer(serializers.Serializer):
    propriedade = serializers.IntegerField(required=False, min_value=1)
    safra = serializers.CharField(required=False, allow_blank=True, max_length=20)

    def validate_safra(self, value):
        return value.strip()


def obter_filtros_propriedade_safra(query_params):
    dados = {"safra": query_params.get("safra", "").strip()}
    propriedade = query_params.get("propriedade", "").strip()
    if propriedade:
        dados["propriedade"] = propriedade

    serializer = FiltrosPropriedadeSafraSerializer(data=dados)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data

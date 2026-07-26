from rest_framework import serializers

from .models import ClimaCornBelt, CotacaoMercado, NoticiaMercado


class CotacaoMercadoSerializer(serializers.ModelSerializer):
    produto_nome = serializers.CharField(source="get_produto_display", read_only=True)

    class Meta:
        model = CotacaoMercado
        fields = "__all__"
        read_only_fields = tuple(field.name for field in CotacaoMercado._meta.fields)


class ClimaCornBeltSerializer(serializers.ModelSerializer):
    regiao_nome = serializers.CharField(source="get_regiao_display", read_only=True)

    class Meta:
        model = ClimaCornBelt
        fields = "__all__"
        read_only_fields = tuple(field.name for field in ClimaCornBelt._meta.fields)


class NoticiaMercadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = NoticiaMercado
        fields = "__all__"
        read_only_fields = ("criado_em", "atualizado_em")

    def validate_url(self, value):
        if not value.startswith("https://"):
            raise serializers.ValidationError("Use um endereço HTTPS.")
        return value

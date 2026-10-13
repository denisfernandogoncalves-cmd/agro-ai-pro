from rest_framework import serializers

from .models import CotacaoCBOT, ClimaCornBelt, CotacaoMercado, NoticiaMercado


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


class CotacaoCBOTSerializer(serializers.ModelSerializer):
    produto_nome = serializers.CharField(source="get_produto_display", read_only=True)
    unidade = serializers.SerializerMethodField()
    contrato_completo = serializers.SerializerMethodField()
    aviso = serializers.SerializerMethodField()

    class Meta:
        model = CotacaoCBOT
        fields = "__all__"
        read_only_fields = tuple(field.name for field in CotacaoCBOT._meta.fields)

    def get_unidade(self, obj):
        return "US$/bushel"

    def get_contrato_completo(self, obj):
        import re
        return bool(re.search(r"-\d{4}$",obj.contrato))

    def get_aviso(self, obj):
        return "Cotação com atraso do provedor; não é tempo real nem preço de ajuste oficial. Contrato de referência selecionado pelo provedor, sujeito a mudança de vencimento."

from rest_framework import serializers

from .enterprise_models import AtualizacaoMercado, ConfiguracaoAtivoMercado, CotacaoAtivoMercado


class CotacaoAtivoMercadoSerializer(serializers.ModelSerializer):
    ativo_nome = serializers.CharField(source="get_ativo_display", read_only=True)

    class Meta:
        model = CotacaoAtivoMercado
        fields = "__all__"
        read_only_fields = tuple(field.name for field in CotacaoAtivoMercado._meta.fields)


class ConfiguracaoAtivoMercadoSerializer(serializers.ModelSerializer):
    ativo_nome = serializers.CharField(source="get_ativo_display", read_only=True)

    class Meta:
        model = ConfiguracaoAtivoMercado
        fields = "__all__"
        read_only_fields = (
            "provedor",
            "simbolo",
            "ultima_tentativa",
            "ultima_atualizacao",
            "proxima_atualizacao",
            "status",
            "mensagem_erro",
            "falhas_consecutivas",
            "total_chamadas",
            "total_atualizacoes",
            "atualizado_em",
        )


class AtualizacaoMercadoSerializer(serializers.ModelSerializer):
    ativo_nome = serializers.CharField(source="get_ativo_display", read_only=True)

    class Meta:
        model = AtualizacaoMercado
        fields = "__all__"
        read_only_fields = tuple(field.name for field in AtualizacaoMercado._meta.fields)

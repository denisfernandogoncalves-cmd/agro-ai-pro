from rest_framework import serializers

from .models import LinhaImportacao, LoteImportacao


class LinhaImportacaoSerializer(serializers.ModelSerializer):
    propriedade_nome = serializers.CharField(
        source="propriedade.nome",
        read_only=True,
    )
    lote_graos_codigo = serializers.CharField(
        source="lote_graos.codigo",
        read_only=True,
    )

    class Meta:
        model = LinhaImportacao
        fields = "__all__"


class LoteImportacaoSerializer(serializers.ModelSerializer):
    criado_por_nome = serializers.CharField(
        source="criado_por.username",
        read_only=True,
    )
    linhas_url = serializers.SerializerMethodField()

    class Meta:
        model = LoteImportacao
        fields = "__all__"

    def get_linhas_url(self, obj):
        request = self.context.get("request")
        caminho = f"/api/importacoes/linhas/?lote={obj.id}"
        return request.build_absolute_uri(caminho) if request else caminho


class UploadPlanilhaSerializer(serializers.Serializer):
    arquivo = serializers.FileField(allow_empty_file=False)


class ResultadoPreviewSerializer(serializers.Serializer):
    lote = LoteImportacaoSerializer(read_only=True)
    linhas_preview = LinhaImportacaoSerializer(many=True, read_only=True)
    preview_limitado = serializers.BooleanField(read_only=True)

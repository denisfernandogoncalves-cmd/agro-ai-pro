from rest_framework import serializers

from .models import ConfirmacaoImportacao, LinhaImportacao, LoteImportacao


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


class ConfirmarLoteImportacaoSerializer(serializers.Serializer):
    confirmar = serializers.BooleanField()
    idempotency_key = serializers.RegexField(
        regex=r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,99}$",
        min_length=8,
        max_length=100,
        trim_whitespace=True,
    )

    def validate_confirmar(self, value):
        if value is not True:
            raise serializers.ValidationError(
                "A confirmação exige a declaração explícita confirmar=true."
            )
        return value


class ResultadoConfirmacaoSerializer(serializers.Serializer):
    lote_id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=LoteImportacao.Status.choices)
    idempotency_key = serializers.CharField()
    usuario_confirmador = serializers.CharField()
    confirmado_em = serializers.DateTimeField()
    total_linhas = serializers.IntegerField()
    total_movimentacoes_criadas = serializers.IntegerField()
    linhas_rejeitadas = serializers.IntegerField()
    movimentacoes_ids = serializers.ListField(
        child=serializers.IntegerField(),
    )
    replay_idempotente = serializers.BooleanField()
    saldos_afetados = serializers.ListField(child=serializers.DictField())


class ConfirmacaoImportacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfirmacaoImportacao
        fields = "__all__"

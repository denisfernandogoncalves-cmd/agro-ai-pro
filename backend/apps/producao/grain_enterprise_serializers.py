from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .grain_enterprise_models import (
    ConfiguracaoCultura,
    DetalheLocalArmazenagem,
    NotaFiscalProducao,
    OrigemTerceiroRecebimento,
    TransferenciaGraos,
)
from .grain_serializers import (
    EmbarqueProducaoSerializer,
    RecebimentoProducaoSerializer,
)


class FullCleanEnterpriseSerializerMixin:
    def validate(self, attrs):
        instance = self.instance or self.Meta.model()
        for field, value in attrs.items():
            setattr(instance, field, value)
        try:
            instance.full_clean(exclude=None)
        except DjangoValidationError as exc:
            detail = exc.message_dict if hasattr(exc, "message_dict") else {"detail": exc.messages}
            raise serializers.ValidationError(detail) from exc
        return attrs


class ConfiguracaoCulturaSerializer(
    FullCleanEnterpriseSerializerMixin,
    serializers.ModelSerializer,
):
    cultura_nome = serializers.CharField(source="cultura.nome", read_only=True)

    class Meta:
        model = ConfiguracaoCultura
        fields = "__all__"
        read_only_fields = ("atualizado_em",)


class DetalheLocalArmazenagemSerializer(
    FullCleanEnterpriseSerializerMixin,
    serializers.ModelSerializer,
):
    local_nome = serializers.CharField(source="local.nome", read_only=True)
    propriedade = serializers.IntegerField(source="local.propriedade_id", read_only=True)
    propriedade_nome = serializers.CharField(source="local.propriedade.nome", read_only=True)

    class Meta:
        model = DetalheLocalArmazenagem
        fields = "__all__"
        read_only_fields = ("criado_em", "atualizado_em")


class OrigemTerceiroRecebimentoSerializer(
    FullCleanEnterpriseSerializerMixin,
    serializers.ModelSerializer,
):
    terceiro_nome = serializers.CharField(source="terceiro.nome", read_only=True)

    class Meta:
        model = OrigemTerceiroRecebimento
        fields = "__all__"
        read_only_fields = ("criado_em",)


class TransferenciaGraosSerializer(
    FullCleanEnterpriseSerializerMixin,
    serializers.ModelSerializer,
):
    cultura_nome = serializers.CharField(source="cultura.nome", read_only=True)
    safra_nome = serializers.CharField(source="safra.nome", read_only=True)
    propriedade_origem_nome = serializers.CharField(
        source="propriedade_origem.nome",
        read_only=True,
    )
    propriedade_destino_nome = serializers.CharField(
        source="propriedade_destino.nome",
        read_only=True,
    )
    cadpro_origem_codigo = serializers.CharField(source="cadpro_origem.codigo", read_only=True)
    cadpro_destino_codigo = serializers.CharField(source="cadpro_destino.codigo", read_only=True)
    local_origem_nome = serializers.CharField(source="local_origem.nome", read_only=True)
    local_destino_nome = serializers.CharField(source="local_destino.nome", read_only=True)
    talhao_origem_nome = serializers.CharField(source="talhao_origem.nome", read_only=True)
    talhao_destino_nome = serializers.CharField(source="talhao_destino.nome", read_only=True)
    criado_por_nome = serializers.CharField(source="criado_por.username", read_only=True)
    confirmado_por_nome = serializers.CharField(source="confirmado_por.username", read_only=True)

    class Meta:
        model = TransferenciaGraos
        fields = "__all__"
        read_only_fields = (
            "status",
            "movimento_saida",
            "movimento_entrada",
            "criado_por",
            "confirmado_por",
            "confirmado_em",
            "criado_em",
            "atualizado_em",
        )

    def create(self, validated_data):
        return TransferenciaGraos.objects.create(
            criado_por=self.context["request"].user,
            **validated_data,
        )


class NotaFiscalProducaoSerializer(
    FullCleanEnterpriseSerializerMixin,
    serializers.ModelSerializer,
):
    propriedade_nome = serializers.CharField(source="propriedade.nome", read_only=True)
    cadpro_codigo = serializers.CharField(source="cadpro.codigo", read_only=True)
    criado_por_nome = serializers.CharField(source="criado_por.username", read_only=True)

    class Meta:
        model = NotaFiscalProducao
        fields = "__all__"
        read_only_fields = ("criado_por", "criado_em")

    def create(self, validated_data):
        return NotaFiscalProducao.objects.create(
            criado_por=self.context["request"].user,
            **validated_data,
        )


class RecebimentoEnterpriseSerializer(RecebimentoProducaoSerializer):
    terceiro_id = serializers.SerializerMethodField()
    terceiro_nome = serializers.SerializerMethodField()
    notas_fiscais = NotaFiscalProducaoSerializer(many=True, read_only=True)

    class Meta(RecebimentoProducaoSerializer.Meta):
        fields = "__all__"

    def get_terceiro_id(self, obj):
        origem = getattr(obj, "origem_terceiro", None)
        return origem.terceiro_id if origem else None

    def get_terceiro_nome(self, obj):
        origem = getattr(obj, "origem_terceiro", None)
        return origem.terceiro.nome if origem else None


class EmbarqueEnterpriseSerializer(EmbarqueProducaoSerializer):
    notas_fiscais = NotaFiscalProducaoSerializer(many=True, read_only=True)

    class Meta(EmbarqueProducaoSerializer.Meta):
        fields = "__all__"

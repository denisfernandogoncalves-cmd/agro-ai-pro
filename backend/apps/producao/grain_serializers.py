from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .grain_models import (
    AcessoCadPro,
    AuditoriaProducao,
    CadPro,
    ContratoProducao,
    Cultura,
    EmbarqueProducao,
    ImportacaoPlanilha,
    Motorista,
    MovimentacaoGraos,
    RecebimentoProducao,
    Safra,
    SaldoGraos,
    Veiculo,
)


class FullCleanSerializerMixin:
    def validate(self, attrs):
        instance = self.instance or self.Meta.model()
        for field, value in attrs.items():
            setattr(instance, field, value)
        try:
            instance.clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc
        return attrs


class CulturaSerializer(FullCleanSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = Cultura
        fields = "__all__"
        read_only_fields = ("criado_em",)


class SafraSerializer(FullCleanSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = Safra
        fields = "__all__"
        read_only_fields = ("criado_em",)


class CadProSerializer(FullCleanSerializerMixin, serializers.ModelSerializer):
    propriedade_nome = serializers.CharField(source="propriedade.nome", read_only=True)

    class Meta:
        model = CadPro
        fields = "__all__"
        read_only_fields = ("criado_em", "atualizado_em")


class AcessoCadProSerializer(serializers.ModelSerializer):
    cadpro_codigo = serializers.CharField(source="cadpro.codigo", read_only=True)
    propriedade_id = serializers.IntegerField(source="cadpro.propriedade_id", read_only=True)
    usuario_nome = serializers.CharField(source="usuario.username", read_only=True)

    class Meta:
        model = AcessoCadPro
        fields = "__all__"
        read_only_fields = ("criado_em",)


class MotoristaSerializer(serializers.ModelSerializer):
    terceiro_nome = serializers.CharField(source="terceiro.nome", read_only=True)

    class Meta:
        model = Motorista
        fields = "__all__"
        read_only_fields = ("criado_em",)


class VeiculoSerializer(serializers.ModelSerializer):
    motorista_nome = serializers.CharField(source="motorista_padrao.nome", read_only=True)
    terceiro_nome = serializers.CharField(source="terceiro.nome", read_only=True)

    class Meta:
        model = Veiculo
        fields = "__all__"
        read_only_fields = ("criado_em",)


class ContratoProducaoSerializer(FullCleanSerializerMixin, serializers.ModelSerializer):
    propriedade_nome = serializers.CharField(source="propriedade.nome", read_only=True)
    cadpro_codigo = serializers.CharField(source="cadpro.codigo", read_only=True)
    cultura_nome = serializers.CharField(source="cultura.nome", read_only=True)
    safra_nome = serializers.CharField(source="safra.nome", read_only=True)
    comprador_nome = serializers.CharField(source="comprador.nome", read_only=True)
    quantidade_embarcada_kg = serializers.SerializerMethodField()
    saldo_contrato_kg = serializers.SerializerMethodField()

    class Meta:
        model = ContratoProducao
        fields = "__all__"
        read_only_fields = ("criado_em", "atualizado_em")

    def get_quantidade_embarcada_kg(self, obj):
        return sum(
            (item.quantidade_kg for item in obj.embarques.all() if item.status == EmbarqueProducao.Status.CONFIRMADO),
            start=0,
        )

    def get_saldo_contrato_kg(self, obj):
        return max(obj.quantidade_kg - self.get_quantidade_embarcada_kg(obj), 0)


class RecebimentoProducaoSerializer(FullCleanSerializerMixin, serializers.ModelSerializer):
    propriedade_nome = serializers.CharField(source="propriedade.nome", read_only=True)
    cadpro_codigo = serializers.CharField(source="cadpro.codigo", read_only=True)
    talhao_nome = serializers.CharField(source="talhao.nome", read_only=True)
    cultura_nome = serializers.CharField(source="cultura.nome", read_only=True)
    safra_nome = serializers.CharField(source="safra.nome", read_only=True)
    local_nome = serializers.CharField(source="local_armazenagem.nome", read_only=True)
    motorista_nome = serializers.CharField(source="motorista.nome", read_only=True)
    placa = serializers.SerializerMethodField()

    class Meta:
        model = RecebimentoProducao
        fields = "__all__"
        read_only_fields = (
            "status",
            "quantidade_sacas",
            "movimentacao",
            "criado_por",
            "criado_em",
            "atualizado_em",
        )

    def get_placa(self, obj):
        return obj.veiculo.placa if obj.veiculo_id else obj.placa_informada

    def create(self, validated_data):
        return RecebimentoProducao.objects.create(
            criado_por=self.context["request"].user,
            **validated_data,
        )


class SaldoGraosSerializer(serializers.ModelSerializer):
    propriedade_nome = serializers.CharField(source="propriedade.nome", read_only=True)
    cadpro_codigo = serializers.CharField(source="cadpro.codigo", read_only=True)
    talhao_nome = serializers.CharField(source="talhao.nome", read_only=True)
    cultura_nome = serializers.CharField(source="cultura.nome", read_only=True)
    safra_nome = serializers.CharField(source="safra.nome", read_only=True)
    local_nome = serializers.CharField(source="local_armazenagem.nome", read_only=True)
    quantidade_sacas = serializers.DecimalField(max_digits=18, decimal_places=3, read_only=True)

    class Meta:
        model = SaldoGraos
        fields = "__all__"
        read_only_fields = tuple(field.name for field in SaldoGraos._meta.fields)


class MovimentacaoGraosSerializer(serializers.ModelSerializer):
    propriedade_nome = serializers.CharField(source="propriedade.nome", read_only=True)
    cadpro_codigo = serializers.CharField(source="cadpro.codigo", read_only=True)
    cultura_nome = serializers.CharField(source="cultura.nome", read_only=True)
    safra_nome = serializers.CharField(source="safra.nome", read_only=True)
    local_origem_nome = serializers.CharField(source="local_origem.nome", read_only=True)
    local_destino_nome = serializers.CharField(source="local_destino.nome", read_only=True)
    usuario_nome = serializers.CharField(source="criado_por.username", read_only=True)

    class Meta:
        model = MovimentacaoGraos
        fields = "__all__"
        read_only_fields = tuple(field.name for field in MovimentacaoGraos._meta.fields)


class EmbarqueProducaoSerializer(FullCleanSerializerMixin, serializers.ModelSerializer):
    propriedade_nome = serializers.CharField(source="propriedade.nome", read_only=True)
    cadpro_codigo = serializers.CharField(source="cadpro.codigo", read_only=True)
    cultura_nome = serializers.CharField(source="cultura.nome", read_only=True)
    safra_nome = serializers.CharField(source="safra.nome", read_only=True)
    comprador_nome = serializers.CharField(source="comprador.nome", read_only=True)
    contrato_numero = serializers.CharField(source="contrato.numero", read_only=True)
    local_nome = serializers.CharField(source="local_armazenagem.nome", read_only=True)
    motorista_nome = serializers.CharField(source="motorista.nome", read_only=True)
    placa = serializers.SerializerMethodField()

    class Meta:
        model = EmbarqueProducao
        fields = "__all__"
        read_only_fields = (
            "status",
            "quantidade_sacas",
            "valor_total",
            "movimentacao",
            "lancamento_financeiro",
            "criado_por",
            "criado_em",
            "atualizado_em",
        )

    def get_placa(self, obj):
        return obj.veiculo.placa if obj.veiculo_id else obj.placa_informada

    def create(self, validated_data):
        return EmbarqueProducao.objects.create(
            criado_por=self.context["request"].user,
            **validated_data,
        )


class AuditoriaProducaoSerializer(serializers.ModelSerializer):
    usuario_nome = serializers.CharField(source="usuario.username", read_only=True)
    propriedade_nome = serializers.CharField(source="propriedade.nome", read_only=True)

    class Meta:
        model = AuditoriaProducao
        fields = "__all__"
        read_only_fields = tuple(field.name for field in AuditoriaProducao._meta.fields)


class ImportacaoPlanilhaSerializer(serializers.ModelSerializer):
    propriedade_nome = serializers.CharField(source="propriedade.nome", read_only=True)
    cadpro_codigo = serializers.CharField(source="cadpro.codigo", read_only=True)
    usuario_nome = serializers.CharField(source="criado_por.username", read_only=True)

    class Meta:
        model = ImportacaoPlanilha
        fields = "__all__"
        read_only_fields = (
            "nome_original",
            "hash_arquivo",
            "mapeamento",
            "previa",
            "inconsistencias",
            "total_linhas",
            "linhas_importadas",
            "status",
            "criado_por",
            "criado_em",
            "confirmado_em",
        )

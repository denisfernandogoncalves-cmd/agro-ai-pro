from rest_framework import serializers

from apps.graos.models import PosicaoSaldoGraos

from .models import DevolucaoVendaGraos, EntregaVendaGraos, VendaGraos


class VendaGraosCriacaoSerializer(serializers.Serializer):
    numero_contrato = serializers.CharField(max_length=80)
    cliente_nome = serializers.CharField(max_length=160)
    posicao = serializers.PrimaryKeyRelatedField(
        queryset=PosicaoSaldoGraos.objects.select_related("cad_pro", "armazem")
    )
    quantidade_kg = serializers.DecimalField(max_digits=16, decimal_places=3)
    data_contrato = serializers.DateField(required=False)
    data_limite_entrega = serializers.DateField(
        required=False, allow_null=True
    )
    observacoes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        limite = attrs.get("data_limite_entrega")
        contrato = attrs.get("data_contrato")
        if limite and contrato and limite < contrato:
            raise serializers.ValidationError(
                {"data_limite_entrega": "A data limite não pode anteceder o contrato."}
            )
        return attrs


class CancelamentoSerializer(serializers.Serializer):
    observacoes = serializers.CharField(required=False, allow_blank=True)


class MovimentoVendaSerializer(serializers.Serializer):
    quantidade_kg = serializers.DecimalField(max_digits=16, decimal_places=3)
    data_movimento = serializers.DateField(required=False)
    referencia_externa = serializers.CharField(
        max_length=120, required=False, allow_blank=True
    )
    observacoes = serializers.CharField(required=False, allow_blank=True)


class EntregaVendaSerializer(serializers.ModelSerializer):
    movimentacao_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = EntregaVendaGraos
        fields = (
            "id", "quantidade_kg", "data_entrega", "referencia_externa",
            "observacoes", "movimentacao_id", "criado_em",
        )


class DevolucaoVendaSerializer(serializers.ModelSerializer):
    movimentacao_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = DevolucaoVendaGraos
        fields = (
            "id", "quantidade_kg", "data_devolucao", "referencia_externa",
            "observacoes", "movimentacao_id", "criado_em",
        )


class VendaGraosSerializer(serializers.ModelSerializer):
    cad_pro = serializers.UUIDField(source="posicao.cad_pro_id", read_only=True)
    cad_pro_codigo = serializers.CharField(
        source="posicao.cad_pro.codigo", read_only=True
    )
    cultura = serializers.CharField(source="posicao.cultura", read_only=True)
    safra = serializers.CharField(source="posicao.safra", read_only=True)
    classificacao_codigo = serializers.CharField(
        source="posicao.classificacao_codigo", read_only=True
    )
    armazem = serializers.IntegerField(
        source="posicao.armazem_id", read_only=True
    )
    armazem_nome = serializers.CharField(
        source="posicao.armazem.nome", read_only=True
    )
    propriedade = serializers.IntegerField(
        source="posicao.armazem.propriedade_id", read_only=True
    )
    propriedade_nome = serializers.CharField(
        source="posicao.armazem.propriedade.nome", read_only=True
    )
    lote_codigo = serializers.CharField(source="lote.codigo", read_only=True)
    quantidade_reservada_kg = serializers.DecimalField(
        max_digits=16, decimal_places=3, read_only=True
    )
    quantidade_aberta_kg = serializers.DecimalField(
        max_digits=16, decimal_places=3, read_only=True
    )
    criado_por_nome = serializers.CharField(
        source="criado_por.username", read_only=True
    )
    entregas = EntregaVendaSerializer(many=True, read_only=True)
    devolucoes = DevolucaoVendaSerializer(many=True, read_only=True)
    origens_colheita = serializers.SerializerMethodField()

    class Meta:
        model = VendaGraos
        fields = (
            "id", "numero_contrato", "cliente_nome", "status", "posicao",
            "lote", "lote_codigo", "cad_pro", "cad_pro_codigo", "cultura",
            "safra", "classificacao_codigo", "armazem", "armazem_nome",
            "propriedade", "propriedade_nome", "quantidade_kg",
            "quantidade_reservada_kg", "quantidade_entregue_kg",
            "quantidade_devolvida_kg", "quantidade_cancelada_kg",
            "quantidade_aberta_kg", "data_contrato", "data_limite_entrega",
            "reserva", "observacoes", "origens_colheita", "entregas",
            "devolucoes", "criado_por_nome", "confirmado_em", "cancelado_em",
            "criado_em", "atualizado_em",
        )

    def get_origens_colheita(self, obj):
        return [
            {
                "carga_id": carga.pk,
                "data_colheita": carga.data_colheita,
                "placa": carga.placa,
                "peso_liquido_kg": carga.peso_liquido_kg,
                "grupo_id": carga.grupo_colheita_id,
                "grupo_nome": carga.grupo_colheita.nome,
            }
            for carga in list(obj.lote.cargas_colhidas.all())[:20]
        ]

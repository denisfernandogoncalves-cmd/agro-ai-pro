from decimal import Decimal

from rest_framework import serializers

from apps.cadpro.models import CADPro
from apps.propriedades.models import Propriedade
from apps.graos.models import ArmazemGraos, PosicaoSaldoGraos

from .models import ContratoComercial, DevolucaoVendaGraos, EntregaVendaGraos, VendaGraos


class ContratoComercialSerializer(serializers.ModelSerializer):
    quantidade_kg = serializers.DecimalField(max_digits=16, decimal_places=3, min_value=Decimal("0.001"))
    produto = serializers.CharField(max_length=80, allow_blank=False)

    class Meta:
        model = ContratoComercial
        fields = ("id", "numero", "empresa", "quantidade_kg", "produto", "ativo")


class NovaPosicaoVendaSerializer(serializers.Serializer):
    propriedade = serializers.PrimaryKeyRelatedField(queryset=Propriedade.objects.all())
    cad_pro = serializers.PrimaryKeyRelatedField(queryset=CADPro.objects.filter(ativo=True))
    cultura = serializers.ChoiceField(choices=("Soja", "Milho", "Trigo"))
    safra = serializers.CharField(max_length=20)
    classificacao_codigo = serializers.CharField(max_length=50, default="PADRAO")
    armazem = serializers.PrimaryKeyRelatedField(queryset=ArmazemGraos.objects.filter(ativo=True))


class VendaGraosCriacaoSerializer(serializers.Serializer):
    contrato = serializers.PrimaryKeyRelatedField(queryset=ContratoComercial.objects.all(), required=False, allow_null=True)
    numero_contrato = serializers.CharField(max_length=80, required=False, allow_blank=True, default="")
    cliente_nome = serializers.CharField(max_length=160, required=False, allow_blank=True)
    posicao = serializers.PrimaryKeyRelatedField(
        queryset=PosicaoSaldoGraos.objects.select_related("cad_pro", "armazem"), required=False
    )
    nova_posicao = NovaPosicaoVendaSerializer(required=False)
    quantidade_kg = serializers.DecimalField(max_digits=16, decimal_places=3)
    data_contrato = serializers.DateField(required=False)
    data_limite_entrega = serializers.DateField(
        required=False, allow_null=True
    )
    observacoes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if attrs.get("posicao") and attrs.get("nova_posicao"):
            raise serializers.ValidationError("Informe a posição existente ou os dados de uma nova posição, nunca ambos.")
        if not self.partial and not attrs.get("posicao") and not attrs.get("nova_posicao") and not attrs.get("contexto_particular"):
            raise serializers.ValidationError("Selecione a posição ou informe cultura, safra e armazenagem para iniciar o saldo.")
        if self.partial and attrs.get("nova_posicao"):
            raise serializers.ValidationError("Para editar, selecione uma posição existente.")
        if attrs.get("contrato"):
            attrs["numero_contrato"] = attrs["contrato"].numero
            attrs["cliente_nome"] = attrs["contrato"].empresa
        elif not self.partial:
            attrs["cliente_nome"] = attrs.get("cliente_nome") or attrs.get("destino", "").strip()
            if not attrs["cliente_nome"]:
                raise serializers.ValidationError({"cliente_nome": "Informe o comprador ou destino da venda."})
        elif "cliente_nome" in attrs and not attrs["cliente_nome"]:
            raise serializers.ValidationError({"cliente_nome": "Informe o comprador da venda."})
        limite = attrs.get("data_limite_entrega")
        contrato = attrs.get("data_contrato")
        if limite and contrato and limite < contrato:
            raise serializers.ValidationError(
                {"data_limite_entrega": "A data limite não pode anteceder o contrato."}
            )
        return attrs


class CancelamentoSerializer(serializers.Serializer):
    observacoes = serializers.CharField(required=False, allow_blank=True)


class AlteracaoSerializer(serializers.Serializer):
    versao = serializers.IntegerField(min_value=1)
    motivo = serializers.CharField(max_length=500, allow_blank=False)


class EdicaoVendaSerializer(VendaGraosCriacaoSerializer):
    versao = serializers.IntegerField(min_value=1)
    motivo = serializers.CharField(max_length=500, allow_blank=False)


class MovimentoVendaSerializer(serializers.Serializer):
    quantidade_kg = serializers.DecimalField(max_digits=16, decimal_places=3)
    data_movimento = serializers.DateField(required=False)
    referencia_externa = serializers.CharField(
        max_length=120, required=False, allow_blank=True
    )
    observacoes = serializers.CharField(required=False, allow_blank=True)


class EntregaMovimentoVendaSerializer(MovimentoVendaSerializer):
    destino = serializers.CharField(max_length=160, required=False, allow_blank=True)
    placa = serializers.CharField(max_length=12, required=False, allow_blank=True)
    motorista = serializers.CharField(max_length=160, required=False, allow_blank=True)
    nota_produtor = serializers.CharField(max_length=80, required=False, allow_blank=True)
    nota_empresa = serializers.CharField(max_length=80, required=False, allow_blank=True)


class ContextoParticularSerializer(serializers.Serializer):
    cultura = serializers.ChoiceField(choices=("Soja", "Milho", "Trigo"))
    safra = serializers.CharField(max_length=20, allow_blank=False)
    classificacao_codigo = serializers.CharField(max_length=50, default="PADRAO")
    armazem = serializers.PrimaryKeyRelatedField(queryset=ArmazemGraos.objects.filter(ativo=True))

    def validate_classificacao_codigo(self, valor):
        return valor.strip().upper()


class PreviaParticularSerializer(serializers.Serializer):
    contexto_particular = ContextoParticularSerializer()
    quantidade_kg = serializers.DecimalField(max_digits=16, decimal_places=3, min_value=Decimal("0.001"))


class SaidaVendaSerializer(VendaGraosCriacaoSerializer, EntregaMovimentoVendaSerializer):
    """Um lançamento reúne o contexto comercial e os dados da saída."""
    contexto_particular = ContextoParticularSerializer(required=False)
    hash_previa = serializers.CharField(max_length=64, min_length=64, required=False)

    def validate(self, attrs):
        particular = attrs.get("destino", "").strip().upper() == "PARTICULAR"
        if particular:
            if not attrs.get("contexto_particular") or not attrs.get("hash_previa"):
                raise serializers.ValidationError("Para venda PARTICULAR, informe produto, safra, armazenagem e confira o rateio por área.")
            if attrs.get("posicao") or attrs.get("nova_posicao"):
                raise serializers.ValidationError("Venda PARTICULAR usa todas as propriedades; não selecione uma posição individual.")
            attrs["destino"] = "PARTICULAR"
        elif attrs.get("contexto_particular") or attrs.get("hash_previa"):
            raise serializers.ValidationError("O rateio por área é exclusivo do destino PARTICULAR.")
        return super().validate(attrs)


class EntregaVendaSerializer(serializers.ModelSerializer):
    movimentacao_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = EntregaVendaGraos
        fields = (
            "id", "quantidade_kg", "data_entrega", "referencia_externa",
            "destino", "placa", "motorista", "nota_produtor", "nota_empresa",
            "observacoes", "movimentacao_id", "criado_em", "cancelado_em",
        )


class DevolucaoVendaSerializer(serializers.ModelSerializer):
    movimentacao_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = DevolucaoVendaGraos
        fields = (
            "id", "quantidade_kg", "data_devolucao", "referencia_externa",
            "observacoes", "movimentacao_id", "criado_em", "cancelado_em",
        )


class VendaGraosSerializer(serializers.ModelSerializer):
    rateio_particular_id = serializers.IntegerField(read_only=True, allow_null=True)
    rateio_particular_snapshot = serializers.JSONField(source="rateio_particular.snapshot", read_only=True)
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
        source="posicao.propriedade_id", read_only=True, allow_null=True
    )
    propriedade_nome = serializers.CharField(
        source="posicao.propriedade.nome", read_only=True, allow_null=True
    )
    lote_operacional = serializers.IntegerField(source="lote_id", read_only=True)
    lote_operacional_codigo = serializers.CharField(
        source="lote.codigo", read_only=True
    )
    origem_fisica_alocada = serializers.BooleanField(read_only=True, default=False)
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
    alteracoes = serializers.SerializerMethodField()

    def get_alteracoes(self, obj):
        return [{"id": a.pk, "tipo": a.tipo, "motivo": a.motivo, "criado_em": a.criado_em,
                 "usuario": a.criado_por.username} for a in obj.alteracoes.all()]

    class Meta:
        model = VendaGraos
        fields = (
            "rateio_particular_id", "rateio_particular_snapshot",
            "id", "numero_contrato", "cliente_nome", "status", "posicao", "contrato", "versao", "excluida_em", "alteracoes",
            "lote_operacional", "lote_operacional_codigo",
            "origem_fisica_alocada", "cad_pro", "cad_pro_codigo", "cultura",
            "safra", "classificacao_codigo", "armazem", "armazem_nome",
            "propriedade", "propriedade_nome", "quantidade_kg",
            "quantidade_reservada_kg", "quantidade_entregue_kg",
            "quantidade_devolvida_kg", "quantidade_cancelada_kg",
            "quantidade_aberta_kg", "data_contrato", "data_limite_entrega",
            "reserva", "observacoes", "entregas",
            "devolucoes", "criado_por_nome", "confirmado_em", "cancelado_em",
            "criado_em", "atualizado_em",
        )

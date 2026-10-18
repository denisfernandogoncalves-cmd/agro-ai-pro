from rest_framework import serializers
from django.utils import timezone
from apps.core.correcoes import VersaoCorrecaoSerializer

from .models import Caminhao, LancamentoTransporte, RemuneracaoMotorista





class CaminhaoSerializer(VersaoCorrecaoSerializer, serializers.ModelSerializer):

    class Meta:

        model = Caminhao

        fields = "__all__"



    def to_internal_value(self, data):

        data = data.copy()

        if "placa" in data:

            data["placa"] = str(data["placa"]).upper().replace("-", "").replace(" ", "")

        return super().to_internal_value(data)





class LancamentoSerializer(VersaoCorrecaoSerializer, serializers.ModelSerializer):

    valor_unitario = serializers.DecimalField(max_digits=14, decimal_places=4, min_value=0, required=False)
    compra_diesel_esperada = serializers.IntegerField(write_only=True, required=False, min_value=1)
    preco_diesel_esperado = serializers.DecimalField(write_only=True, required=False, max_digits=14, decimal_places=4)
    compra_diesel_data = serializers.DateField(source="compra_diesel.data", read_only=True)

    def validate(self, attrs):
        compra_esperada = attrs.pop("compra_diesel_esperada", None)
        preco_esperado = attrs.pop("preco_diesel_esperado", None)
        silo = attrs.get("abasteceu_silo", getattr(self.instance, "abasteceu_silo", False))
        if silo:
            tipo = attrs.get("tipo", getattr(self.instance, "tipo", None))
            diesel = attrs.get("tipo_diesel", getattr(self.instance, "tipo_diesel", ""))
            data = attrs.get("data", getattr(self.instance, "data", timezone.localdate()))
            if tipo != "despesa":
                raise serializers.ValidationError({"tipo": "Abastecimento no silo deve ser uma despesa."})
            if not diesel:
                raise serializers.ValidationError({"tipo_diesel": "Selecione S10 ou S500."})
            recalcular = self.instance is None or not self.instance.abasteceu_silo or data != self.instance.data or diesel != self.instance.tipo_diesel
            if recalcular:
                from .diesel import ultima_compra_diesel
                compra = ultima_compra_diesel(data, diesel)
                if (compra_esperada is not None and compra_esperada != compra.pk) or (preco_esperado is not None and preco_esperado != compra.valor_unitario):
                    raise serializers.ValidationError("O preço de referência mudou. Consulte novamente antes de salvar.")
                attrs.update(compra_diesel=compra, valor_unitario=compra.valor_unitario)
            else:
                attrs["valor_unitario"] = self.instance.valor_unitario
            attrs.update(unidade="L", local="Silo")
        else:
            attrs.update(compra_diesel=None, tipo_diesel="")
            if "valor_unitario" not in attrs and self.instance is None:
                raise serializers.ValidationError({"valor_unitario": "Informe o valor unitário."})
            if self.instance and self.instance.abasteceu_silo and "valor_unitario" not in attrs:
                raise serializers.ValidationError({"valor_unitario": "Informe o preço ao retirar o abastecimento no silo."})
        return attrs

    placa = serializers.CharField(source="caminhao.placa", read_only=True)

    total = serializers.DecimalField(max_digits=22, decimal_places=2, read_only=True)



    class Meta:

        model = LancamentoTransporte

        fields = "__all__"

        read_only_fields = ("criado_em", "origem", "chave_importacao", "compra_diesel")





class RemuneracaoSerializer(VersaoCorrecaoSerializer, serializers.ModelSerializer):
    comissao_manual = serializers.DecimalField(source="comissao", max_digits=14, decimal_places=2, read_only=True)
    comissao_transportes = serializers.DecimalField(source="valor_comissao_transporte", max_digits=22, decimal_places=2, read_only=True)
    comissao_fretes = serializers.DecimalField(max_digits=22, decimal_places=2, read_only=True)


    comissao = serializers.DecimalField(source="valor_comissao", max_digits=22, decimal_places=2, read_only=True)

    base_comissao = serializers.DecimalField(max_digits=22, decimal_places=2, read_only=True)

    placa = serializers.CharField(source="caminhao.placa", read_only=True)



    class Meta:

        model = RemuneracaoMotorista

        fields = "__all__"



    def validate(self, attrs):
        if self.instance and self.instance.fretes_conferidos.exists() and any(k in attrs and attrs[k] != getattr(self.instance, k) for k in ("caminhao", "motorista", "competencia")):
            raise serializers.ValidationError("Esta remuneração possui fretes conferidos. Preserve motorista, placa e competência.")

        if attrs.get("comissao_percentual", getattr(self.instance, "comissao_percentual", None)) is None:

            raise serializers.ValidationError({"comissao_percentual": "Informe o percentual da comissão."})

        return attrs



    def update(self, instance, validated_data):
        if any(k in validated_data and validated_data[k] != getattr(instance, k) for k in ("caminhao", "motorista", "competencia")):
            validated_data["base_por_aba"] = False
        return super().update(instance, validated_data)

    def validate_competencia(self, value):

        if value.day != 1:

            raise serializers.ValidationError("Use o primeiro dia do mês de competência.")

        return value

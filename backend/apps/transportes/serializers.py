from rest_framework import serializers
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

    placa = serializers.CharField(source="caminhao.placa", read_only=True)

    total = serializers.DecimalField(max_digits=22, decimal_places=2, read_only=True)



    class Meta:

        model = LancamentoTransporte

        fields = "__all__"

        read_only_fields = ("criado_em", "origem", "chave_importacao")





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

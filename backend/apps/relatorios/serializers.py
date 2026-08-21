from rest_framework import serializers


class FiltrosRelatorioOperacionalSerializer(serializers.Serializer):
    cad_pro = serializers.UUIDField(required=False)
    propriedade = serializers.IntegerField(required=False, min_value=1)
    proprietario = serializers.CharField(required=False, allow_blank=True, max_length=100)
    cultura = serializers.CharField(required=False, allow_blank=True, max_length=50)
    safra = serializers.CharField(required=False, allow_blank=True, max_length=20)
    classificacao_codigo = serializers.CharField(
        required=False, allow_blank=True, max_length=50
    )
    armazem = serializers.IntegerField(required=False, min_value=1)
    destinado_semente = serializers.BooleanField(required=False)
    motorista = serializers.CharField(required=False, allow_blank=True, max_length=120)
    placa = serializers.CharField(required=False, allow_blank=True, max_length=12)
    numero_contrato = serializers.CharField(required=False, allow_blank=True, max_length=80)
    comprador = serializers.CharField(required=False, allow_blank=True, max_length=160)
    data_inicio = serializers.DateField(required=False)
    data_fim = serializers.DateField(required=False)
    secao = serializers.ChoiceField(
        required=False,
        default="saldos",
        choices=(
            "saldos",
            "producao",
            "reservas",
            "vendas",
            "entregas",
            "movimentacoes",
            "rastreabilidade",
            "produtividade",
            "motoristas",
        ),
    )
    pagina = serializers.IntegerField(required=False, default=1, min_value=1)
    por_pagina = serializers.IntegerField(
        required=False, default=25, min_value=1, max_value=100
    )

    def validate(self, attrs):
        inicio = attrs.get("data_inicio")
        fim = attrs.get("data_fim")
        if inicio and fim and inicio > fim:
            raise serializers.ValidationError(
                {"data_fim": "A data final deve ser igual ou posterior à inicial."}
            )
        for campo in (
            "proprietario", "cultura", "safra", "classificacao_codigo",
            "motorista", "placa", "numero_contrato", "comprador",
        ):
            if campo in attrs:
                attrs[campo] = attrs[campo].strip()
        if attrs.get("classificacao_codigo"):
            attrs["classificacao_codigo"] = attrs["classificacao_codigo"].upper()
        return attrs

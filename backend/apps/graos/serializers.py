from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import ArmazemGraos, LoteGraos, MovimentacaoGraos
from .services import registrar_movimentacao, saldo_armazem


class ArmazemGraosSerializer(serializers.ModelSerializer):
    propriedade_nome = serializers.CharField(
        source="propriedade.nome",
        read_only=True,
    )
    ocupacao_kg = serializers.SerializerMethodField()

    class Meta:
        model = ArmazemGraos
        fields = "__all__"
        read_only_fields = ("criado_em", "atualizado_em")

    def get_ocupacao_kg(self, obj):
        return saldo_armazem(obj)

    def validate(self, attrs):
        propriedade_original = (
            self.instance.propriedade_id if self.instance else None
        )
        instancia = self.instance or ArmazemGraos()
        for campo, valor in attrs.items():
            setattr(instancia, campo, valor)
        try:
            instancia.full_clean(exclude=("id",))
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc
        if self.instance:
            ocupacao = saldo_armazem(self.instance)
            capacidade = attrs.get("capacidade_kg", self.instance.capacidade_kg)
            propriedade = attrs.get("propriedade")
            if (
                propriedade
                and propriedade.id != propriedade_original
                and self.instance.lotes.exists()
            ):
                raise serializers.ValidationError(
                    {
                        "propriedade": (
                            "A propriedade do armazém não pode mudar após a "
                            "criação de lotes."
                        )
                    }
                )
            if capacidade < ocupacao:
                raise serializers.ValidationError(
                    {
                        "capacidade_kg": (
                            f"A capacidade não pode ser menor que a ocupação atual "
                            f"de {ocupacao} kg."
                        )
                    }
                )
        return attrs


class LoteGraosSerializer(serializers.ModelSerializer):
    armazem_nome = serializers.CharField(source="armazem.nome", read_only=True)
    propriedade_id = serializers.IntegerField(
        source="armazem.propriedade_id",
        read_only=True,
    )
    propriedade_nome = serializers.CharField(
        source="armazem.propriedade.nome",
        read_only=True,
    )
    talhao_nome = serializers.CharField(source="talhao.nome", read_only=True)

    class Meta:
        model = LoteGraos
        fields = "__all__"
        read_only_fields = ("criado_em", "atualizado_em")

    def validate(self, attrs):
        originais = {}
        if self.instance:
            originais = {
                "armazem": self.instance.armazem_id,
                "talhao": self.instance.talhao_id,
                "cultura": self.instance.cultura,
                "safra": self.instance.safra,
            }
        instancia = self.instance or LoteGraos()
        for campo, valor in attrs.items():
            setattr(instancia, campo, valor)
        try:
            instancia.full_clean(exclude=("id",))
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc
        if self.instance and self.instance.movimentacoes.exists():
            alterados = []
            for campo in ("armazem", "talhao"):
                if campo in attrs:
                    novo_id = getattr(attrs[campo], "id", None)
                    if novo_id != originais[campo]:
                        alterados.append(campo)
            alterados.extend(
                campo
                for campo in ("cultura", "safra")
                if campo in attrs and attrs[campo] != originais[campo]
            )
            if alterados:
                raise serializers.ValidationError(
                    {
                        "detail": (
                            "O contexto do lote não pode mudar após a primeira "
                            "movimentação."
                        )
                    }
                )
        return attrs


class MovimentacaoGraosSerializer(serializers.ModelSerializer):
    lote_codigo = serializers.CharField(source="lote.codigo", read_only=True)
    cultura = serializers.CharField(source="lote.cultura", read_only=True)
    safra = serializers.CharField(source="lote.safra", read_only=True)
    armazem_id = serializers.IntegerField(
        source="lote.armazem_id",
        read_only=True,
    )
    propriedade_id = serializers.IntegerField(
        source="lote.armazem.propriedade_id",
        read_only=True,
    )
    criado_por_nome = serializers.CharField(
        source="criado_por.username",
        read_only=True,
    )
    chave_idempotencia = serializers.CharField(
        max_length=160,
        required=False,
        allow_blank=True,
        write_only=True,
    )

    class Meta:
        model = MovimentacaoGraos
        fields = (
            "id",
            "tipo",
            "lote",
            "lote_codigo",
            "cultura",
            "safra",
            "armazem_id",
            "propriedade_id",
            "quantidade_kg",
            "data_movimento",
            "referencia_externa",
            "chave_idempotencia",
            "observacoes",
            "criado_por",
            "criado_por_nome",
            "criado_em",
        )
        read_only_fields = ("criado_por", "criado_em")

    def create(self, validated_data):
        try:
            return registrar_movimentacao(
                usuario=self.context["request"].user,
                **validated_data,
            )
        except ValueError as exc:
            raise serializers.ValidationError({"detail": str(exc)}) from exc


class TransferenciaGraosSerializer(serializers.Serializer):
    lote_destino = serializers.PrimaryKeyRelatedField(
        queryset=LoteGraos.objects.select_related("armazem"),
    )
    quantidade_kg = serializers.DecimalField(
        max_digits=16,
        decimal_places=3,
        min_value=Decimal("0.001"),
    )
    data_movimento = serializers.DateField()
    observacoes = serializers.CharField(required=False, allow_blank=True)
    chave_idempotencia = serializers.CharField(
        max_length=150,
        required=False,
        allow_blank=True,
    )


class FiltrosGraosSerializer(serializers.Serializer):
    propriedade = serializers.IntegerField(required=False, min_value=1)
    armazem = serializers.IntegerField(required=False, min_value=1)
    cultura = serializers.CharField(required=False, allow_blank=True, max_length=50)
    safra = serializers.CharField(required=False, allow_blank=True, max_length=20)

    def validate_cultura(self, value):
        return value.strip()

    def validate_safra(self, value):
        return value.strip()

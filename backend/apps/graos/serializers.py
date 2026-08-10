from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import (
    ArmazemGraos,
    CargaColhida,
    GrupoColheita,
    LoteGraos,
    MovimentacaoGraos,
    OrigemSaldoGraos,
    PosicaoSaldoGraos,
    ReservaSaldoGraos,
)
from .cargas_services import registrar_carga_colhida
from .services import ResultadoOperacaoSaldo, registrar_movimentacao, saldo_armazem


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


class GrupoColheitaSerializer(serializers.ModelSerializer):
    propriedade_nome = serializers.CharField(source="propriedade.nome", read_only=True)
    cad_pro_codigo = serializers.CharField(source="cad_pro.codigo", read_only=True)
    criado_por_nome = serializers.CharField(source="criado_por.username", read_only=True)

    class Meta:
        model = GrupoColheita
        fields = "__all__"
        read_only_fields = ("criado_por", "criado_em", "atualizado_em")

    def validate(self, attrs):
        instancia = self.instance or GrupoColheita()
        for campo, valor in attrs.items():
            setattr(instancia, campo, valor)
        try:
            instancia.full_clean(exclude=("id", "criado_por"))
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc
        return attrs

    def create(self, validated_data):
        grupo = GrupoColheita(
            criado_por=self.context["request"].user,
            **validated_data,
        )
        grupo.full_clean()
        grupo.save()
        return grupo


class CargaColhidaSerializer(serializers.ModelSerializer):
    placa = serializers.CharField(max_length=12)
    propriedade = serializers.IntegerField(
        source="grupo_colheita.propriedade_id",
        read_only=True,
    )
    propriedade_nome = serializers.CharField(
        source="grupo_colheita.propriedade.nome",
        read_only=True,
    )
    grupo_colheita_nome = serializers.CharField(
        source="grupo_colheita.nome",
        read_only=True,
    )
    cad_pro = serializers.IntegerField(source="grupo_colheita.cad_pro_id", read_only=True)
    cad_pro_codigo = serializers.CharField(
        source="grupo_colheita.cad_pro.codigo",
        read_only=True,
    )
    armazem_nome = serializers.CharField(source="armazem.nome", read_only=True)
    lote_codigo = serializers.CharField(source="lote.codigo", read_only=True)
    criado_por_nome = serializers.CharField(source="criado_por.username", read_only=True)

    class Meta:
        model = CargaColhida
        fields = "__all__"
        read_only_fields = (
            "lote",
            "desconto_total_percentual",
            "desconto_total_kg",
            "peso_liquido_kg",
            "sacas_60kg",
            "regra_desconto_aplicada",
            "fingerprint",
            "movimentacao",
            "criado_por",
            "criado_em",
        )

    def create(self, validated_data):
        return registrar_carga_colhida(
            usuario=self.context["request"].user,
            **validated_data,
        )


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
    cad_pro_codigo = serializers.CharField(source="cad_pro.codigo", read_only=True)

    class Meta:
        model = LoteGraos
        fields = "__all__"
        read_only_fields = ("criado_em", "atualizado_em")

    def validate(self, attrs):
        originais = {}
        if self.instance:
            originais = {
                "armazem": self.instance.armazem_id,
                "cad_pro": self.instance.cad_pro_id,
                "talhao": self.instance.talhao_id,
                "cultura": self.instance.cultura,
                "safra": self.instance.safra,
                "classificacao_codigo": self.instance.classificacao_codigo,
            }
        elif not attrs.get("cad_pro"):
            raise serializers.ValidationError(
                {"cad_pro": "O CAD/PRO é obrigatório para novos lotes."}
            )
        instancia = self.instance or LoteGraos()
        for campo, valor in attrs.items():
            setattr(instancia, campo, valor)
        try:
            instancia.full_clean(exclude=("id",))
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc
        if self.instance and self.instance.movimentacoes.exists():
            alterados = []
            for campo in ("armazem", "cad_pro", "talhao"):
                if campo in attrs:
                    novo_id = getattr(attrs[campo], "id", None)
                    if novo_id != originais[campo]:
                        alterados.append(campo)
            alterados.extend(
                campo
                for campo in ("cultura", "safra", "classificacao_codigo")
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
        required=True,
        allow_blank=False,
        write_only=True,
    )

    class Meta:
        model = MovimentacaoGraos
        fields = (
            "id",
            "tipo",
            "operacao",
            "lote",
            "lote_codigo",
            "cultura",
            "safra",
            "armazem_id",
            "propriedade_id",
            "quantidade_kg",
            "delta_fisico_kg",
            "delta_comprometido_kg",
            "snapshot_anterior",
            "snapshot_posterior",
            "posicao",
            "origem",
            "reserva",
            "estorno_de",
            "data_movimento",
            "referencia_externa",
            "chave_idempotencia",
            "observacoes",
            "criado_por",
            "criado_por_nome",
            "criado_em",
        )
        read_only_fields = (
            "operacao",
            "delta_fisico_kg",
            "delta_comprometido_kg",
            "snapshot_anterior",
            "snapshot_posterior",
            "posicao",
            "origem",
            "reserva",
            "estorno_de",
            "criado_por",
            "criado_em",
        )

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
        required=True,
        allow_blank=False,
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


class PosicaoSaldoGraosSerializer(serializers.ModelSerializer):
    saldo_disponivel_kg = serializers.DecimalField(
        max_digits=16,
        decimal_places=3,
        read_only=True,
    )
    cad_pro_codigo = serializers.CharField(source="cad_pro.codigo", read_only=True)
    armazem_nome = serializers.CharField(source="armazem.nome", read_only=True)
    propriedade_id = serializers.IntegerField(
        source="armazem.propriedade_id",
        read_only=True,
    )

    class Meta:
        model = PosicaoSaldoGraos
        fields = "__all__"


class OrigemSaldoGraosSerializer(serializers.ModelSerializer):
    criado_por_nome = serializers.CharField(source="criado_por.username", read_only=True)
    metadados = serializers.SerializerMethodField()

    class Meta:
        model = OrigemSaldoGraos
        fields = "__all__"

    def get_metadados(self, obj):
        return {
            chave: valor
            for chave, valor in obj.metadados.items()
            if not chave.startswith("_")
        }


class ReservaSaldoGraosSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReservaSaldoGraos
        fields = "__all__"


class OperacaoLoteSerializer(serializers.Serializer):
    lote = serializers.PrimaryKeyRelatedField(
        queryset=LoteGraos.objects.select_related("armazem", "cad_pro")
    )
    quantidade_kg = serializers.DecimalField(
        max_digits=16,
        decimal_places=3,
        min_value=Decimal("0.001"),
    )
    chave_idempotencia = serializers.CharField(max_length=160)
    data_movimento = serializers.DateField(required=False)
    referencia_externa = serializers.CharField(
        max_length=160,
        required=False,
        allow_blank=True,
    )
    observacoes = serializers.CharField(required=False, allow_blank=True)
    metadados = serializers.JSONField(required=False)


class ReservarSaldoSerializer(OperacaoLoteSerializer):
    data_movimento = None


class OperacaoReservaSerializer(serializers.Serializer):
    reserva = serializers.PrimaryKeyRelatedField(
        queryset=ReservaSaldoGraos.objects.select_related("posicao")
    )
    quantidade_kg = serializers.DecimalField(
        max_digits=16,
        decimal_places=3,
        min_value=Decimal("0.001"),
        required=False,
    )
    chave_idempotencia = serializers.CharField(max_length=160)
    data_movimento = serializers.DateField(required=False)
    referencia_externa = serializers.CharField(
        max_length=160,
        required=False,
        allow_blank=True,
    )
    observacoes = serializers.CharField(required=False, allow_blank=True)
    metadados = serializers.JSONField(required=False)


class LiberarReservaSerializer(OperacaoReservaSerializer):
    data_movimento = None


class AjusteSaldoSerializer(serializers.Serializer):
    lote = serializers.PrimaryKeyRelatedField(
        queryset=LoteGraos.objects.select_related("armazem", "cad_pro")
    )
    delta_fisico_kg = serializers.DecimalField(
        max_digits=16,
        decimal_places=3,
    )
    delta_comprometido_kg = serializers.DecimalField(
        max_digits=16,
        decimal_places=3,
        required=False,
        default=Decimal("0.000"),
    )
    chave_idempotencia = serializers.CharField(max_length=160)
    data_movimento = serializers.DateField(required=False)
    referencia_externa = serializers.CharField(max_length=160, required=False, allow_blank=True)
    observacoes = serializers.CharField(required=False, allow_blank=True)
    metadados = serializers.JSONField(required=False)

    def validate(self, attrs):
        if not attrs["delta_fisico_kg"] and not attrs["delta_comprometido_kg"]:
            raise serializers.ValidationError("O ajuste deve alterar ao menos um saldo.")
        return attrs


class EstornoMovimentacaoSerializer(serializers.Serializer):
    movimentacao = serializers.PrimaryKeyRelatedField(
        queryset=MovimentacaoGraos.objects.select_related("posicao", "lote")
    )
    chave_idempotencia = serializers.CharField(max_length=160)
    data_movimento = serializers.DateField(required=False)
    referencia_externa = serializers.CharField(max_length=160, required=False, allow_blank=True)
    observacoes = serializers.CharField(required=False, allow_blank=True)
    metadados = serializers.JSONField(required=False)


class TransferirSaldoFisicoSerializer(serializers.Serializer):
    lote_origem = serializers.PrimaryKeyRelatedField(
        queryset=LoteGraos.objects.select_related("armazem", "cad_pro")
    )
    lote_destino = serializers.PrimaryKeyRelatedField(
        queryset=LoteGraos.objects.select_related("armazem", "cad_pro")
    )
    quantidade_kg = serializers.DecimalField(
        max_digits=16,
        decimal_places=3,
        min_value=Decimal("0.001"),
    )
    chave_idempotencia = serializers.CharField(max_length=160)
    data_movimento = serializers.DateField(required=False)
    referencia_externa = serializers.CharField(max_length=160, required=False, allow_blank=True)
    observacoes = serializers.CharField(required=False, allow_blank=True)
    metadados = serializers.JSONField(required=False)


class ReconciliarPosicaoSerializer(serializers.Serializer):
    posicao = serializers.PrimaryKeyRelatedField(
        queryset=PosicaoSaldoGraos.objects.all()
    )
    chave_idempotencia = serializers.CharField(max_length=160)
    metadados = serializers.JSONField(required=False)


class FiltrosPosicaoSaldoSerializer(serializers.Serializer):
    cad_pro = serializers.UUIDField(required=False)
    cultura = serializers.CharField(required=False, allow_blank=True, max_length=50)
    safra = serializers.CharField(required=False, allow_blank=True, max_length=20)
    classificacao_codigo = serializers.CharField(required=False, allow_blank=True, max_length=50)
    armazem = serializers.IntegerField(required=False, min_value=1)


def serializar_resultado(resultado: ResultadoOperacaoSaldo):
    return {
        "sucesso": True,
        "codigo": resultado.codigo,
        "idempotente": resultado.idempotente,
        "origem": _serializar_origem_dto(resultado.origem),
        "posicoes": [_serializar_posicao_dto(item) for item in resultado.posicoes],
        "movimentacoes": [
            _serializar_movimentacao_dto(item) for item in resultado.movimentacoes
        ],
        "reserva": _serializar_reserva_dto(resultado.reserva),
        "detalhes": _serializar_contrato(resultado.detalhes),
    }


def _id_api(valor):
    return int(valor) if valor and str(valor).isdigit() else valor


def _decimal_api(valor):
    return format(valor, ".3f")


def _serializar_origem_dto(origem):
    return {
        "id": _id_api(origem.id),
        "tipo": origem.tipo,
        "chave_idempotencia": origem.chave_idempotencia,
        "referencia_externa": origem.referencia_externa,
        "hash_requisicao": origem.hash_requisicao,
        "metadados": _serializar_contrato(origem.metadados),
        "criado_por": _id_api(origem.criado_por_id),
        "criado_por_nome": origem.criado_por_nome,
        "criado_em": origem.criado_em,
    }


def _serializar_posicao_dto(posicao):
    return {
        "id": _id_api(posicao.id),
        "cad_pro": posicao.cad_pro_id,
        "cad_pro_codigo": posicao.cad_pro_codigo,
        "cultura": posicao.cultura,
        "safra": posicao.safra,
        "classificacao_codigo": posicao.classificacao_codigo,
        "armazem": _id_api(posicao.armazem_id),
        "armazem_nome": posicao.armazem_nome,
        "propriedade_id": _id_api(posicao.propriedade_id),
        "saldo_fisico_kg": _decimal_api(posicao.saldo_fisico_kg),
        "saldo_comprometido_kg": _decimal_api(posicao.saldo_comprometido_kg),
        "saldo_disponivel_kg": _decimal_api(posicao.saldo_disponivel_kg),
        "versao": int(posicao.versao),
        "criado_em": posicao.criado_em,
        "atualizado_em": posicao.atualizado_em,
    }


def _serializar_movimentacao_dto(movimento):
    return {
        "id": _id_api(movimento.id),
        "tipo": movimento.tipo,
        "operacao": movimento.operacao,
        "lote": _id_api(movimento.lote_id),
        "lote_codigo": movimento.lote_codigo,
        "cultura": movimento.cultura,
        "safra": movimento.safra,
        "armazem_id": _id_api(movimento.armazem_id),
        "propriedade_id": _id_api(movimento.propriedade_id),
        "quantidade_kg": _decimal_api(movimento.quantidade_kg),
        "delta_fisico_kg": _decimal_api(movimento.delta_fisico_kg),
        "delta_comprometido_kg": _decimal_api(movimento.delta_comprometido_kg),
        "snapshot_anterior": _serializar_contrato(movimento.snapshot_anterior),
        "snapshot_posterior": _serializar_contrato(movimento.snapshot_posterior),
        "posicao": _id_api(movimento.posicao_id),
        "origem": _id_api(movimento.origem_id),
        "reserva": _id_api(movimento.reserva_id),
        "estorno_de": _id_api(movimento.estorno_de_id),
        "data_movimento": movimento.data_movimento,
        "referencia_externa": movimento.referencia_externa,
        "observacoes": movimento.observacoes,
        "criado_por": _id_api(movimento.criado_por_id),
        "criado_por_nome": movimento.criado_por_nome,
        "criado_em": movimento.criado_em,
    }


def _serializar_reserva_dto(reserva):
    if not reserva:
        return None
    return {
        "id": _id_api(reserva.id),
        "posicao": _id_api(reserva.posicao_id),
        "origem": _id_api(reserva.origem_id),
        "quantidade_kg": _decimal_api(reserva.quantidade_kg),
        "saldo_reservado_kg": _decimal_api(reserva.saldo_reservado_kg),
        "referencia_externa": reserva.referencia_externa,
        "status": reserva.status,
        "criado_por": _id_api(reserva.criado_por_id),
        "criado_em": reserva.criado_em,
        "atualizado_em": reserva.atualizado_em,
    }


def _serializar_contrato(valor):
    if hasattr(valor, "items"):
        return {
            chave: _serializar_contrato(item)
            for chave, item in valor.items()
        }
    if isinstance(valor, (tuple, frozenset)):
        return [_serializar_contrato(item) for item in valor]
    return valor

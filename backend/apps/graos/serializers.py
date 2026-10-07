from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from apps.cadpro.models import CADPro
from apps.propriedades.models import Propriedade

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
from .cargas_services import corrigir_carga_colhida, registrar_carga_colhida
from .services import ResultadoOperacaoSaldo, registrar_movimentacao, saldo_armazem


class UUIDPrimaryKeyRelatedField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        return str(super().to_representation(value))


class ArmazemGraosSerializer(serializers.ModelSerializer):
    propriedade = serializers.PrimaryKeyRelatedField(read_only=True)
    propriedade_nome = serializers.SerializerMethodField()
    ocupacao_kg = serializers.SerializerMethodField()

    class Meta:
        model = ArmazemGraos
        fields = "__all__"
        read_only_fields = ("criado_em", "atualizado_em")

    def get_ocupacao_kg(self, obj):
        return saldo_armazem(obj)

    def get_propriedade_nome(self, obj):
        return obj.propriedade.nome if obj.propriedade_id else None

    def validate(self, attrs):
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

    @transaction.atomic
    def update(self, instance, validated_data):
        armazem = (
            ArmazemGraos.objects.select_for_update()
            .get(pk=instance.pk)
        )
        ocupacao = saldo_armazem(armazem)
        capacidade = validated_data.get("capacidade_kg", armazem.capacidade_kg)
        if capacidade < ocupacao:
            raise serializers.ValidationError(
                {
                    "capacidade_kg": (
                        "A capacidade não pode ser menor que a ocupação atual "
                        f"de {ocupacao} kg."
                    )
                }
            )
        for campo, valor in validated_data.items():
            setattr(armazem, campo, valor)
        try:
            armazem.full_clean(exclude=("id",))
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc
        armazem.save()
        return armazem


class GrupoColheitaSerializer(serializers.ModelSerializer):
    cad_pro = UUIDPrimaryKeyRelatedField(queryset=CADPro.objects.all())
    propriedade_nome = serializers.CharField(source="propriedade.nome", read_only=True)
    cad_pro_codigo = serializers.CharField(source="cad_pro.codigo", read_only=True)
    criado_por_nome = serializers.CharField(source="criado_por.username", read_only=True)
    armazem_padrao_nome = serializers.CharField(
        source="armazem_padrao.nome",
        read_only=True,
    )
    contexto_congelado = serializers.SerializerMethodField()

    class Meta:
        model = GrupoColheita
        fields = "__all__"
        read_only_fields = (
            "armazem_padrao",
            "tolerancia_umidade_percentual",
            "desconto_umidade_por_ponto",
            "criado_por",
            "criado_em",
            "atualizado_em",
        )

    def get_contexto_congelado(self, obj):
        if hasattr(obj, "contexto_congelado_db"):
            return obj.contexto_congelado_db
        return obj.cargas.exists()

    def validate(self, attrs):
        cultura = attrs.get("cultura", getattr(self.instance, "cultura", ""))
        if " ".join(str(cultura).strip().upper().split()) not in {
            "SOJA",
            "MILHO",
            "TRIGO",
        }:
            raise serializers.ValidationError(
                {"cultura": "A cultura deve ser Soja, Milho ou Trigo."}
            )
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

    @transaction.atomic
    def update(self, instance, validated_data):
        grupo = GrupoColheita.objects.select_for_update().get(pk=instance.pk)
        for campo, valor in validated_data.items():
            setattr(grupo, campo, valor)
        try:
            grupo.save()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc
        return grupo


class CargaColhidaSerializer(serializers.ModelSerializer):
    placa = serializers.CharField(max_length=12, required=False, allow_blank=True)
    motorista = serializers.CharField(max_length=120, required=False, allow_blank=True)
    propriedade = serializers.PrimaryKeyRelatedField(
        queryset=Propriedade.objects.all(),
    )
    cad_pro = UUIDPrimaryKeyRelatedField(queryset=CADPro.objects.all())
    talhoes_selecionados = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        write_only=True,
        required=False,
        default=list,
    )
    propriedades_selecionadas = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        write_only=True,
        required=False,
        default=list,
    )
    cadpros_por_propriedade = serializers.DictField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False,
        default=dict,
    )
    propriedade_nome = serializers.CharField(
        source="propriedade.nome",
        read_only=True,
    )
    cad_pro_codigo = serializers.CharField(
        source="cad_pro.codigo",
        read_only=True,
    )
    armazem_nome = serializers.CharField(source="armazem.nome", read_only=True)
    lote_codigo = serializers.CharField(source="lote.codigo", read_only=True)
    criado_por_nome = serializers.CharField(source="criado_por.username", read_only=True)
    cancelada_por_nome = serializers.CharField(
        source="cancelada_por.username",
        read_only=True,
    )
    motivo_correcao = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        max_length=500,
    )
    chave_registro = serializers.RegexField(
        regex=r"^[A-Za-z0-9._:-]{8,100}$",
        write_only=True,
        required=False,
        allow_blank=True,
        max_length=100,
        error_messages={
            "invalid": "A chave de registro da carga é inválida.",
        },
    )
    tolerancia_impureza_percentual = serializers.DecimalField(
        write_only=True,
        required=False,
        default=Decimal("0.00"),
        max_digits=5,
        decimal_places=2,
        min_value=Decimal("0"),
        max_value=Decimal("100"),
    )
    desconto_impureza_por_ponto = serializers.DecimalField(
        write_only=True,
        required=False,
        default=Decimal("1.000"),
        max_digits=6,
        decimal_places=3,
        min_value=Decimal("0"),
        max_value=Decimal("100"),
    )
    tolerancia_defeitos_percentual = serializers.DecimalField(
        write_only=True,
        required=False,
        default=Decimal("0.00"),
        max_digits=5,
        decimal_places=2,
        min_value=Decimal("0"),
        max_value=Decimal("100"),
    )
    desconto_defeitos_por_ponto = serializers.DecimalField(
        write_only=True,
        required=False,
        default=Decimal("1.000"),
        max_digits=6,
        decimal_places=3,
        min_value=Decimal("0"),
        max_value=Decimal("100"),
    )
    ph_minimo = serializers.DecimalField(
        write_only=True,
        required=False,
        default=Decimal("0.00"),
        max_digits=5,
        decimal_places=2,
        min_value=Decimal("0"),
        max_value=Decimal("100"),
    )
    desconto_ph_por_ponto = serializers.DecimalField(
        write_only=True,
        required=False,
        default=Decimal("0.000"),
        max_digits=6,
        decimal_places=3,
        min_value=Decimal("0"),
        max_value=Decimal("100"),
    )

    class Meta:
        model = CargaColhida
        fields = (
            "id",
            "propriedade",
            "propriedade_nome",
            "cad_pro",
            "cad_pro_codigo",
            "cultura",
            "safra",
            "armazem",
            "armazem_nome",
            "lote",
            "lote_codigo",
            "data_colheita",
            "placa",
            "motorista",
            "peso_total_kg",
            "tara_kg",
            "peso_bruto_kg",
            "umidade_percentual",
            "impureza_percentual",
            "defeitos_percentual",
            "ph",
            "destinado_semente",
            "local_colheita",
            "talhoes_selecionados",
            "propriedades_selecionadas",
            "cadpros_por_propriedade",
            "tolerancia_impureza_percentual",
            "desconto_impureza_por_ponto",
            "tolerancia_defeitos_percentual",
            "desconto_defeitos_por_ponto",
            "ph_minimo",
            "desconto_ph_por_ponto",
            "desconto_total_percentual",
            "desconto_total_kg",
            "peso_liquido_kg",
            "sacas_60kg",
            "regra_desconto_aplicada",
            "contexto_colheita",
            "fingerprint",
            "movimentacao",
            "observacoes",
            "status",
            "cancelada_em",
            "cancelada_por",
            "cancelada_por_nome",
            "motivo_cancelamento",
            "motivo_correcao",
            "chave_registro",
            "substituida_por",
            "criado_por",
            "criado_por_nome",
            "criado_em",
        )
        read_only_fields = (
            "lote",
            "desconto_total_percentual",
            "desconto_total_kg",
            "peso_liquido_kg",
            "sacas_60kg",
            "regra_desconto_aplicada",
            "contexto_colheita",
            "fingerprint",
            "movimentacao",
            "status",
            "cancelada_em",
            "cancelada_por",
            "motivo_cancelamento",
            "substituida_por",
            "criado_por",
            "criado_em",
        )

    def validate_cultura(self, value):
        cultura = " ".join(str(value or "").strip().split()).title()
        if cultura.upper() not in {"SOJA", "MILHO", "TRIGO"}:
            raise serializers.ValidationError("A cultura deve ser Soja, Milho ou Trigo.")
        return cultura

    def validate_safra(self, value):
        safra = " ".join(str(value or "").strip().split())
        if not safra:
            raise serializers.ValidationError("Informe a safra da carga.")
        return safra

    def create(self, validated_data):
        validated_data.pop("motivo_correcao", None)
        return registrar_carga_colhida(
            usuario=self.context["request"].user,
            request=self.context['request'],
            **validated_data,
        )

    @staticmethod
    def _regras_atuais(instance):
        parcelas = (instance.regra_desconto_aplicada or {}).get("parcelas", {})
        impureza = parcelas.get("impureza", {})
        defeitos = parcelas.get("defeitos", {})
        ph = parcelas.get("ph", {})
        return {
            "tolerancia_impureza_percentual": impureza.get(
                "tolerancia_percentual", "100.00"
            ),
            "desconto_impureza_por_ponto": impureza.get(
                "desconto_por_ponto", "0.000"
            ),
            "tolerancia_defeitos_percentual": defeitos.get(
                "tolerancia_percentual", "100.00"
            ),
            "desconto_defeitos_por_ponto": defeitos.get(
                "desconto_por_ponto", "0.000"
            ),
            "ph_minimo": ph.get("minimo", "0.00"),
            "desconto_ph_por_ponto": ph.get("desconto_por_ponto", "0.000"),
        }

    def update(self, instance, validated_data):
        motivo = validated_data.pop(
            "motivo_correcao", "Correção solicitada pelo usuário."
        )
        validated_data.pop("chave_registro", None)
        regras = self._regras_atuais(instance)
        for campo in tuple(regras):
            if campo in validated_data:
                regras[campo] = validated_data.pop(campo)
        talhoes = validated_data.pop(
            "talhoes_selecionados",
            [
                item["id"]
                for item in (instance.contexto_colheita or {}).get("talhoes", [])
                if item.get("id")
            ],
        )
        propriedades = validated_data.pop(
            "propriedades_selecionadas",
            [
                item["id"]
                for item in (instance.contexto_colheita or {}).get("propriedades", [])
                if item.get("id")
            ],
        )
        cadpros_por_propriedade = validated_data.pop(
            "cadpros_por_propriedade",
            {
                str(item["id"]): item["cad_pro_id"]
                for item in (instance.contexto_colheita or {}).get(
                    "propriedades", []
                )
                if item.get("id") and item.get("cad_pro_id")
            },
        )
        campos = (
            "propriedade",
            "cad_pro",
            "cultura",
            "safra",
            "armazem",
            "data_colheita",
            "placa",
            "motorista",
            "peso_total_kg",
            "tara_kg",
            "peso_bruto_kg",
            "umidade_percentual",
            "impureza_percentual",
            "defeitos_percentual",
            "ph",
            "destinado_semente",
            "local_colheita",
            "observacoes",
        )
        dados = {
            campo: validated_data.get(campo, getattr(instance, campo))
            for campo in campos
        }
        dados.update(regras)
        dados["talhoes_selecionados"] = talhoes
        dados["propriedades_selecionadas"] = propriedades
        dados["cadpros_por_propriedade"] = cadpros_por_propriedade
        return corrigir_carga_colhida(
            usuario=self.context["request"].user,
            request=self.context['request'],
            carga=instance,
            motivo=motivo,
            **dados,
        )


class LoteGraosSerializer(serializers.ModelSerializer):
    cad_pro = UUIDPrimaryKeyRelatedField(queryset=CADPro.objects.all())
    armazem_nome = serializers.CharField(source="armazem.nome", read_only=True)
    propriedade_id = serializers.IntegerField(
        read_only=True,
        allow_null=True,
    )
    propriedade_nome = serializers.CharField(
        source="propriedade.nome",
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
                "propriedade": self.instance.propriedade_id,
                "cad_pro": self.instance.cad_pro_id,
                "talhao": self.instance.talhao_id,
                "cultura": self.instance.cultura,
                "safra": self.instance.safra,
                "classificacao_codigo": self.instance.classificacao_codigo,
            }
        else:
            erros = {}
            if not attrs.get("propriedade"):
                erros["propriedade"] = "A propriedade produtora é obrigatória."
            if not attrs.get("cad_pro"):
                erros["cad_pro"] = "O CAD/PRO é obrigatório para novos lotes."
            if erros:
                raise serializers.ValidationError(erros)
        instancia = self.instance or LoteGraos()
        for campo, valor in attrs.items():
            setattr(instancia, campo, valor)
        try:
            instancia.full_clean(exclude=("id",))
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc
        if self.instance and self.instance.movimentacoes.exists():
            alterados = []
            for campo in ("armazem", "propriedade", "cad_pro", "talhao"):
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

    @transaction.atomic
    def update(self, instance, validated_data):
        lote_bloqueado = LoteGraos.objects.select_for_update().get(pk=instance.pk)
        campos_estruturais = (
            "armazem",
            "propriedade",
            "cad_pro",
            "talhao",
            "cultura",
            "safra",
            "classificacao_codigo",
        )
        alterados = []
        for campo in campos_estruturais:
            if campo not in validated_data:
                continue
            valor_atual = getattr(lote_bloqueado, f"{campo}_id", None)
            novo_valor = validated_data[campo]
            if campo in ("armazem", "propriedade", "cad_pro", "talhao"):
                novo_valor = getattr(novo_valor, "pk", None)
            else:
                valor_atual = getattr(lote_bloqueado, campo)
            if novo_valor != valor_atual:
                alterados.append(campo)
        if alterados and lote_bloqueado.movimentacoes.exists():
            raise serializers.ValidationError(
                {
                    "detail": (
                        "O contexto do lote não pode mudar após a primeira "
                        "movimentação."
                    )
                }
            )
        return super().update(lote_bloqueado, validated_data)


class MovimentacaoGraosSerializer(serializers.ModelSerializer):
    estornado = serializers.SerializerMethodField()
    correcao_transferencia = serializers.SerializerMethodField()

    def get_estornado(self, obj):
        return hasattr(obj, "movimento_estorno")

    def get_correcao_transferencia(self, obj):
        correcao = getattr(obj.origem, "correcao_transferencia", None)
        if not correcao:
            return None
        return {"acao": correcao.acao, "motivo": correcao.motivo,
                "origem_nova": correcao.origem_nova_id,
                "criado_em": correcao.criado_em.isoformat(),
                "criado_por_nome": correcao.criado_por.username}

    lote_codigo = serializers.CharField(source="lote.codigo", read_only=True)
    cultura = serializers.CharField(source="posicao.cultura", read_only=True)
    safra = serializers.CharField(source="posicao.safra", read_only=True)
    classificacao_codigo = serializers.CharField(
        source="posicao.classificacao_codigo",
        read_only=True,
    )
    cad_pro = serializers.UUIDField(source="posicao.cad_pro_id", read_only=True)
    cad_pro_codigo = serializers.CharField(source="posicao.cad_pro.codigo", read_only=True)
    armazem_id = serializers.IntegerField(
        source="posicao.armazem_id",
        read_only=True,
    )
    propriedade_id = serializers.IntegerField(
        source="posicao.propriedade_id",
        read_only=True,
    )
    armazem_nome = serializers.CharField(source="posicao.armazem.nome", read_only=True)
    origem_tipo = serializers.CharField(source="origem.tipo", read_only=True)
    origem_chave_idempotencia = serializers.CharField(
        source="origem.chave_idempotencia",
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
            "classificacao_codigo",
            "cad_pro",
            "cad_pro_codigo",
            "armazem_id",
            "armazem_nome",
            "propriedade_id",
            "quantidade_kg",
            "delta_fisico_kg",
            "delta_comprometido_kg",
            "snapshot_anterior",
            "snapshot_posterior",
            "posicao",
            "origem",
            "origem_tipo",
            "origem_chave_idempotencia",
            "reserva",
            "estorno_de",
            "estornado",
            "correcao_transferencia",
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
    propriedade_nome = serializers.CharField(
        source="propriedade.nome", read_only=True, allow_null=True,
    )
    cad_pro = serializers.UUIDField(source="cad_pro_id", read_only=True)
    saldo_disponivel_kg = serializers.DecimalField(
        max_digits=16,
        decimal_places=3,
        read_only=True,
    )
    cad_pro_codigo = serializers.CharField(source="cad_pro.codigo", read_only=True)
    armazem_nome = serializers.CharField(source="armazem.nome", read_only=True)
    propriedade_id = serializers.IntegerField(
        read_only=True,
        allow_null=True,
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
    propriedade_destino = serializers.PrimaryKeyRelatedField(queryset=Propriedade.objects.all(), required=False)
    cad_pro_destino = serializers.PrimaryKeyRelatedField(queryset=CADPro.objects.all(), required=False)
    posicao_origem = serializers.PrimaryKeyRelatedField(
        queryset=PosicaoSaldoGraos.objects.select_related("armazem", "cad_pro", "propriedade"),
        required=False,
        write_only=True,
    )
    posicao_destino = serializers.PrimaryKeyRelatedField(
        queryset=PosicaoSaldoGraos.objects.select_related("armazem", "cad_pro", "propriedade"),
        required=False,
        write_only=True,
    )
    lote_origem = serializers.PrimaryKeyRelatedField(
        queryset=LoteGraos.objects.select_related("armazem", "cad_pro"),
        required=False,
        write_only=True,
    )
    lote_destino = serializers.PrimaryKeyRelatedField(
        queryset=LoteGraos.objects.select_related("armazem", "cad_pro"),
        required=False,
        write_only=True,
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

    @staticmethod
    def _lote_adaptador(posicao):
        return (
            LoteGraos.objects.select_related("armazem", "cad_pro")
            .filter(
                ativo=True,
                propriedade_id=posicao.propriedade_id,
                cad_pro_id=posicao.cad_pro_id,
                cultura=posicao.cultura,
                safra=posicao.safra,
                classificacao_codigo=posicao.classificacao_codigo,
                armazem_id=posicao.armazem_id,
            )
            .order_by("pk")
            .first()
        )

    def validate(self, attrs):
        if "propriedade_destino" in attrs or "cad_pro_destino" in attrs:
            if ("propriedade_destino" not in attrs or "cad_pro_destino" not in attrs
                    or "posicao_origem" not in attrs
                    or any(campo in attrs for campo in ("posicao_destino", "lote_origem", "lote_destino"))):
                raise serializers.ValidationError(
                    "Informe somente posição de origem, propriedade e CAD/PRO de destino."
                )
            lote = self._lote_adaptador(attrs.pop("posicao_origem"))
            if not lote:
                raise serializers.ValidationError("A origem não possui um adaptador operacional ativo.")
            attrs["lote_origem"] = lote
            return attrs
        informou_posicao = "posicao_origem" in attrs or "posicao_destino" in attrs
        informou_lote = "lote_origem" in attrs or "lote_destino" in attrs
        if informou_posicao and informou_lote:
            raise serializers.ValidationError(
                "Informe posições oficiais ou lotes legados, nunca os dois formatos."
            )
        if informou_posicao:
            if "posicao_origem" not in attrs or "posicao_destino" not in attrs:
                raise serializers.ValidationError(
                    "Informe a posição oficial de origem e a posição oficial de destino."
                )
            if attrs["posicao_origem"].pk == attrs["posicao_destino"].pk:
                raise serializers.ValidationError(
                    "A origem e o destino devem ser posições oficiais diferentes."
                )
            for lado in ("origem", "destino"):
                posicao = attrs.pop(f"posicao_{lado}")
                lote = self._lote_adaptador(posicao)
                if not lote:
                    raise serializers.ValidationError({
                        f"posicao_{lado}": (
                            "A posição não possui um adaptador operacional ativo. "
                            "Atualize os cadastros de produção antes de transferir."
                        )
                    })
                attrs[f"lote_{lado}"] = lote
        elif "lote_origem" not in attrs or "lote_destino" not in attrs:
            raise serializers.ValidationError(
                "Informe a posição oficial de origem e a posição oficial de destino."
            )
        return attrs


class ReconciliarPosicaoSerializer(serializers.Serializer):
    posicao = serializers.PrimaryKeyRelatedField(
        queryset=PosicaoSaldoGraos.objects.all()
    )
    chave_idempotencia = serializers.CharField(max_length=160)
    metadados = serializers.JSONField(required=False)


class FiltrosPosicaoSaldoSerializer(serializers.Serializer):
    cad_pro = serializers.UUIDField(required=False)
    propriedade = serializers.IntegerField(required=False, min_value=1)
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


def serializar_painel_saldos(resultado):
    from django.db.models import Sum
    from .models import MovimentoProducaoTerceiro
    recebidos = list(MovimentoProducaoTerceiro.objects.filter(
        tipo='transferencia', estorno__isnull=True,
        movimentacao_saldo__posicao__in=resultado['posicoes'],
    ).values('movimentacao_saldo__posicao_id').annotate(quantidade=Sum('quantidade_kg')))
    from .models import MovimentacaoGraos
    composicao = list(MovimentacaoGraos.objects.filter(posicao__in=resultado['posicoes']).values(
        'operacao','origem__metadados__tipo',
    ).annotate(fisico=Sum('delta_fisico_kg'),comprometido=Sum('delta_comprometido_kg')))
    campos_saldo = (
        "saldo_fisico_kg",
        "saldo_comprometido_kg",
        "saldo_disponivel_kg",
    )
    resumo = dict(resultado["resumo"])
    for campo in campos_saldo:
        resumo[campo] = _decimal_api(resumo[campo])
    consolidados = []
    for item in resultado["consolidado_cadpro"]:
        consolidado = dict(item)
        for campo in campos_saldo:
            consolidado[campo] = _decimal_api(consolidado[campo])
        consolidados.append(consolidado)
    propriedades = []
    for item in resultado["consolidado_propriedade"]:
        propriedade = dict(item)
        for campo in campos_saldo:
            propriedade[campo] = _decimal_api(propriedade[campo])
        propriedades.append(propriedade)
    return {
        'recebimentos_terceiros': [{'posicao':r['movimentacao_saldo__posicao_id'],'quantidade_kg':_decimal_api(r['quantidade'])} for r in recebidos],
        'composicao': [{'operacao':r['operacao'],'origem_externa':r['origem__metadados__tipo']=='transferencia_terceiro','fisico_kg':_decimal_api(r['fisico']),'comprometido_kg':_decimal_api(r['comprometido'])} for r in composicao],
        "resumo": resumo,
        "consolidado_cadpro": consolidados,
        "consolidado_propriedade": propriedades,
        "posicoes": PosicaoSaldoGraosSerializer(
            resultado["posicoes"],
            many=True,
        ).data,
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

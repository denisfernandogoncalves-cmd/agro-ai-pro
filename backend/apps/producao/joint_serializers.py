from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from apps.core.access import PAPEIS_ADMINISTRACAO, PAPEIS_GESTAO, exigir_acesso_propriedade

from .grain_access import exigir_acesso_cadpro
from .joint_models import (
    CadProLoteConjunto,
    CargaLoteConjunto,
    LoteConjuntoProducao,
    MovimentacaoLoteConjunto,
    ParticipanteLoteConjunto,
    SaidaLoteConjunto,
    SaldoLoteConjunto,
    TalhaoParticipanteLoteConjunto,
)
from .joint_services import recalcular_lote, validar_acesso_propriedades


class TalhaoParticipanteSerializer(serializers.ModelSerializer):
    talhao_nome = serializers.CharField(source="talhao.nome", read_only=True)

    class Meta:
        model = TalhaoParticipanteLoteConjunto
        fields = (
            "id",
            "talhao",
            "talhao_nome",
            "area_cadastrada_ha",
            "area_colhida_ha",
            "observacoes",
        )
        read_only_fields = ("id", "talhao_nome")


class ParticipanteLoteConjuntoSerializer(serializers.ModelSerializer):
    propriedade_nome = serializers.CharField(source="propriedade.nome", read_only=True)
    municipio = serializers.CharField(source="propriedade.municipio", read_only=True)
    produtor = serializers.CharField(source="propriedade.proprietario", read_only=True)
    cadpro_codigo = serializers.CharField(source="cadpro.codigo", read_only=True, allow_null=True)
    talhoes = TalhaoParticipanteSerializer(many=True, required=False)

    class Meta:
        model = ParticipanteLoteConjunto
        fields = (
            "id",
            "propriedade",
            "propriedade_nome",
            "municipio",
            "produtor",
            "cadpro",
            "cadpro_codigo",
            "area_cadastrada_ha",
            "area_colhida_ha",
            "percentual_area",
            "quantidade_rateada_kg",
            "metodo_rateio",
            "excesso_area_autorizado",
            "justificativa_excesso_area",
            "justificativa_rateio",
            "observacoes",
            "talhoes",
        )
        read_only_fields = (
            "id",
            "propriedade_nome",
            "municipio",
            "produtor",
            "cadpro_codigo",
            "percentual_area",
            "metodo_rateio",
            "excesso_area_autorizado",
        )


class CargaLoteConjuntoSerializer(serializers.ModelSerializer):
    motorista_nome = serializers.CharField(source="motorista.nome", read_only=True, allow_null=True)
    placa_cavalo = serializers.SerializerMethodField()
    placa_carreta = serializers.SerializerMethodField()
    transportadora_nome = serializers.CharField(source="transportadora.nome", read_only=True, allow_null=True)
    local_nome = serializers.CharField(source="local_armazenagem.nome", read_only=True)
    quantidade_sacas = serializers.DecimalField(max_digits=18, decimal_places=3, read_only=True)

    class Meta:
        model = CargaLoteConjunto
        fields = (
            "id",
            "lote",
            "data_hora",
            "motorista",
            "motorista_nome",
            "veiculo_cavalo",
            "veiculo_carreta",
            "placa_cavalo_informada",
            "placa_carreta_informada",
            "placa_cavalo",
            "placa_carreta",
            "transportadora",
            "transportadora_nome",
            "origem",
            "destino",
            "peso_bruto_kg",
            "tara_kg",
            "peso_liquido_kg",
            "quantidade_sacas",
            "umidade_percentual",
            "impureza_percentual",
            "defeitos_percentual",
            "romaneio",
            "numero_balanca",
            "nota_fiscal",
            "local_armazenagem",
            "local_nome",
            "observacoes",
            "criado_em",
            "atualizado_em",
        )
        read_only_fields = (
            "id",
            "motorista_nome",
            "placa_cavalo",
            "placa_carreta",
            "transportadora_nome",
            "local_nome",
            "quantidade_sacas",
            "criado_em",
            "atualizado_em",
        )

    def get_placa_cavalo(self, obj):
        return obj.veiculo_cavalo.placa if obj.veiculo_cavalo_id else obj.placa_cavalo_informada

    def get_placa_carreta(self, obj):
        return obj.veiculo_carreta.placa if obj.veiculo_carreta_id else obj.placa_carreta_informada

    def validate(self, attrs):
        lote = attrs.get("lote", getattr(self.instance, "lote", None))
        local = attrs.get("local_armazenagem", getattr(self.instance, "local_armazenagem", None))
        if lote and local and lote.local_armazenagem_id != local.pk:
            raise serializers.ValidationError({"local_armazenagem": "A carga deve usar o local do lote."})
        return attrs

    def create(self, validated_data):
        validated_data["criado_por"] = self.context["request"].user
        carga = super().create(validated_data)
        carga.full_clean()
        carga.save()
        recalcular_lote(carga.lote)
        return carga

    def update(self, instance, validated_data):
        carga = super().update(instance, validated_data)
        carga.full_clean()
        carga.save()
        recalcular_lote(carga.lote)
        return carga


class CadProLoteConjuntoSerializer(serializers.ModelSerializer):
    cadpro_codigo = serializers.CharField(source="cadpro.codigo", read_only=True)
    propriedade_nome = serializers.CharField(source="cadpro.propriedade.nome", read_only=True)

    class Meta:
        model = CadProLoteConjunto
        fields = (
            "id",
            "participante",
            "cadpro",
            "cadpro_codigo",
            "propriedade_nome",
            "quantidade_atribuida_kg",
            "metodo_rateio",
            "justificativa",
            "criado_em",
        )
        read_only_fields = fields


class SaldoLoteConjuntoSerializer(serializers.ModelSerializer):
    local_nome = serializers.CharField(source="local_armazenagem.nome", read_only=True)

    class Meta:
        model = SaldoLoteConjunto
        fields = ("id", "lote", "local_armazenagem", "local_nome", "quantidade_kg", "atualizado_em")
        read_only_fields = fields


class MovimentacaoLoteConjuntoSerializer(serializers.ModelSerializer):
    local_origem_nome = serializers.CharField(source="local_origem.nome", read_only=True, allow_null=True)
    local_destino_nome = serializers.CharField(source="local_destino.nome", read_only=True, allow_null=True)
    cadpro_codigo = serializers.CharField(source="cadpro.codigo", read_only=True, allow_null=True)
    usuario = serializers.CharField(source="criado_por.username", read_only=True)

    class Meta:
        model = MovimentacaoLoteConjunto
        fields = (
            "id",
            "lote",
            "tipo",
            "local_origem",
            "local_origem_nome",
            "local_destino",
            "local_destino_nome",
            "participante",
            "cadpro",
            "cadpro_codigo",
            "quantidade_kg",
            "saldo_origem_anterior",
            "saldo_origem_posterior",
            "saldo_destino_anterior",
            "saldo_destino_posterior",
            "referencia_tipo",
            "referencia_id",
            "motivo",
            "estorno_de",
            "usuario",
            "criado_em",
        )
        read_only_fields = fields


class SaidaLoteConjuntoSerializer(serializers.ModelSerializer):
    lote_codigo = serializers.CharField(source="lote.codigo", read_only=True)
    comprador_nome = serializers.CharField(source="comprador.nome", read_only=True, allow_null=True)
    motorista_nome = serializers.CharField(source="motorista.nome", read_only=True, allow_null=True)
    local_nome = serializers.CharField(source="local_armazenagem.nome", read_only=True)
    placa_cavalo = serializers.SerializerMethodField()
    placa_carreta = serializers.SerializerMethodField()

    class Meta:
        model = SaidaLoteConjunto
        fields = (
            "id",
            "lote",
            "lote_codigo",
            "data_hora",
            "local_armazenagem",
            "local_nome",
            "comprador",
            "comprador_nome",
            "contrato",
            "motorista",
            "motorista_nome",
            "veiculo_cavalo",
            "veiculo_carreta",
            "placa_cavalo_informada",
            "placa_carreta_informada",
            "placa_cavalo",
            "placa_carreta",
            "destino",
            "romaneio",
            "nota_produtor",
            "nota_empresa",
            "quantidade_kg",
            "justificativa",
            "status",
            "movimentacao",
            "criado_em",
            "atualizado_em",
        )
        read_only_fields = (
            "id",
            "lote_codigo",
            "local_nome",
            "comprador_nome",
            "motorista_nome",
            "placa_cavalo",
            "placa_carreta",
            "status",
            "movimentacao",
            "criado_em",
            "atualizado_em",
        )

    def get_placa_cavalo(self, obj):
        return obj.veiculo_cavalo.placa if obj.veiculo_cavalo_id else obj.placa_cavalo_informada

    def get_placa_carreta(self, obj):
        return obj.veiculo_carreta.placa if obj.veiculo_carreta_id else obj.placa_carreta_informada

    def create(self, validated_data):
        validated_data["criado_por"] = self.context["request"].user
        saida = super().create(validated_data)
        saida.full_clean()
        saida.save()
        return saida


class LoteConjuntoProducaoSerializer(serializers.ModelSerializer):
    cultura_nome = serializers.CharField(source="cultura.nome", read_only=True)
    safra_nome = serializers.CharField(source="safra.nome", read_only=True)
    local_nome = serializers.CharField(source="local_armazenagem.nome", read_only=True)
    cadpro_responsavel_codigo = serializers.CharField(source="cadpro_responsavel.codigo", read_only=True, allow_null=True)
    participantes = ParticipanteLoteConjuntoSerializer(many=True)
    cargas = CargaLoteConjuntoSerializer(many=True, read_only=True)
    cadpros_participantes = CadProLoteConjuntoSerializer(many=True, read_only=True)
    saldos_conjuntos = SaldoLoteConjuntoSerializer(many=True, read_only=True)
    quantidade_toneladas = serializers.DecimalField(max_digits=18, decimal_places=3, read_only=True)
    quantidade_sacas = serializers.DecimalField(max_digits=18, decimal_places=3, read_only=True)
    produtividade_kg_ha = serializers.DecimalField(max_digits=18, decimal_places=3, read_only=True)
    produtividade_sacas_ha = serializers.DecimalField(max_digits=18, decimal_places=3, read_only=True)
    quantidade_cargas = serializers.IntegerField(source="cargas.count", read_only=True)

    class Meta:
        model = LoteConjuntoProducao
        fields = (
            "id",
            "codigo",
            "descricao",
            "cultura",
            "cultura_nome",
            "variedade",
            "safra",
            "safra_nome",
            "data_inicio_colheita",
            "data_final_colheita",
            "cadpro_responsavel",
            "cadpro_responsavel_codigo",
            "local_armazenagem",
            "local_nome",
            "modo_rateio",
            "area_total_cadastrada_ha",
            "area_total_colhida_ha",
            "peso_bruto_total_kg",
            "tara_total_kg",
            "peso_liquido_total_kg",
            "quantidade_toneladas",
            "quantidade_sacas",
            "produtividade_kg_ha",
            "produtividade_sacas_ha",
            "umidade_media",
            "impureza_media",
            "defeitos_medios",
            "quantidade_cargas",
            "observacoes",
            "status",
            "participantes",
            "cargas",
            "cadpros_participantes",
            "saldos_conjuntos",
            "criado_em",
            "atualizado_em",
            "confirmado_em",
            "encerrado_em",
            "estornado_em",
        )
        read_only_fields = (
            "id",
            "codigo",
            "cultura_nome",
            "safra_nome",
            "cadpro_responsavel_codigo",
            "local_nome",
            "area_total_cadastrada_ha",
            "area_total_colhida_ha",
            "peso_bruto_total_kg",
            "tara_total_kg",
            "peso_liquido_total_kg",
            "umidade_media",
            "impureza_media",
            "defeitos_medios",
            "status",
            "criado_em",
            "atualizado_em",
            "confirmado_em",
            "encerrado_em",
            "estornado_em",
        )

    def validate_participantes(self, participantes):
        ids = [item["propriedade"].pk for item in participantes]
        if len(set(ids)) < 2:
            raise serializers.ValidationError("Selecione pelo menos duas propriedades distintas.")
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError("Uma propriedade não pode ser duplicada no mesmo lote.")
        return participantes

    def validate(self, attrs):
        if self.instance and self.instance.status not in {
            LoteConjuntoProducao.Status.RASCUNHO,
            LoteConjuntoProducao.Status.CONFERENCIA,
        }:
            raise serializers.ValidationError("Lotes confirmados não podem ser editados diretamente.")
        participantes = attrs.get("participantes")
        if participantes:
            validar_acesso_propriedades(
                self.context["request"].user,
                [item["propriedade"] for item in participantes],
                papeis=PAPEIS_GESTAO,
            )
        return attrs

    def _salvar_participantes(self, lote, participantes):
        usuario = self.context["request"].user
        mantidos = []
        for dados in participantes:
            talhoes = dados.pop("talhoes", [])
            propriedade = dados["propriedade"]
            cadpro = dados.get("cadpro")
            exigir_acesso_propriedade(usuario, propriedade, papeis=PAPEIS_GESTAO)
            if cadpro:
                exigir_acesso_cadpro(usuario, cadpro, papeis=PAPEIS_GESTAO)
            excedeu = Decimal(str(dados["area_colhida_ha"])) > Decimal(str(dados["area_cadastrada_ha"]))
            if excedeu:
                exigir_acesso_propriedade(usuario, propriedade, papeis=PAPEIS_ADMINISTRACAO)
                if not dados.get("justificativa_excesso_area", "").strip():
                    raise serializers.ValidationError(
                        {"participantes": "Área superior à disponível exige justificativa administrativa."}
                    )
                dados["excesso_area_autorizado"] = True
                dados["autorizado_por"] = usuario
            participante, _ = ParticipanteLoteConjunto.objects.update_or_create(
                lote=lote,
                propriedade=propriedade,
                defaults=dados,
            )
            participante.full_clean()
            participante.save()
            mantidos.append(participante.pk)
            talhoes_mantidos = []
            for dados_talhao in talhoes:
                talhao = dados_talhao["talhao"]
                if talhao.propriedade_id != propriedade.pk:
                    raise serializers.ValidationError({"participantes": "Talhão fora da propriedade participante."})
                item, _ = TalhaoParticipanteLoteConjunto.objects.update_or_create(
                    participante=participante,
                    talhao=talhao,
                    defaults=dados_talhao,
                )
                item.full_clean()
                item.save()
                talhoes_mantidos.append(item.pk)
            participante.talhoes.exclude(pk__in=talhoes_mantidos).delete()
        lote.participantes.exclude(pk__in=mantidos).delete()

    @transaction.atomic
    def create(self, validated_data):
        participantes = validated_data.pop("participantes")
        validated_data["criado_por"] = self.context["request"].user
        lote = LoteConjuntoProducao.objects.create(**validated_data)
        self._salvar_participantes(lote, participantes)
        lote.full_clean()
        lote.save()
        return recalcular_lote(lote)

    @transaction.atomic
    def update(self, instance, validated_data):
        participantes = validated_data.pop("participantes", None)
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        instance.full_clean()
        instance.save()
        if participantes is not None:
            self._salvar_participantes(instance, participantes)
        return recalcular_lote(instance)

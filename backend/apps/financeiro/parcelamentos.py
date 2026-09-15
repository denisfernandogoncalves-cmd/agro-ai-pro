"""Parcelas mensais em centavos, gravadas juntas e com repetição idempotente."""
import calendar
import hashlib
import json
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import serializers

from .models import LancamentoFinanceiro, ParcelamentoFinanceiro
from .serializers import LancamentoFinanceiroSerializer


class ParcelamentoSerializer(serializers.Serializer):
    idempotency_key = serializers.UUIDField()
    tipo = serializers.ChoiceField(choices=LancamentoFinanceiro.Tipo.choices)
    descricao = serializers.CharField(max_length=220)
    recebedor_nome = serializers.CharField(max_length=160)
    valor_total = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))
    quantidade = serializers.IntegerField(min_value=1, max_value=120)
    data_emissao = serializers.DateField(default=timezone.localdate)
    primeiro_vencimento = serializers.DateField()
    observacoes = serializers.CharField(required=False, allow_blank=True, default="")
    codigo_barras = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")

    def validate_primeiro_vencimento(self, value):
        return LancamentoFinanceiroSerializer().validate_data_vencimento(value)

    def validate_codigo_barras(self, value):
        return LancamentoFinanceiroSerializer().validate_codigo_barras(value)

    def validate(self, attrs):
        if attrs["valor_total"] * 100 < attrs["quantidade"]:
            raise serializers.ValidationError({"valor_total": "Cada parcela deve ter pelo menos R$ 0,01."})
        if attrs["quantidade"] > 1 and attrs["codigo_barras"]:
            raise serializers.ValidationError({"codigo_barras": "O código de um boleto não pode ser repetido nas parcelas. Informe somente o valor total."})
        ultimo_mes = attrs["primeiro_vencimento"].year * 12 + attrs["primeiro_vencimento"].month - 1 + attrs["quantidade"] - 1
        if ultimo_mes // 12 > 9999:
            raise serializers.ValidationError({"primeiro_vencimento": "As parcelas excedem o limite de datas."})
        return attrs


def calcular_parcelas(total, quantidade, primeiro_vencimento):
    centavos, resto = divmod(int(total * 100), quantidade)
    parcelas = []
    for indice in range(quantidade):
        ano, mes = divmod(primeiro_vencimento.year * 12 + primeiro_vencimento.month - 1 + indice, 12)
        mes += 1
        dia = min(primeiro_vencimento.day, calendar.monthrange(ano, mes)[1])
        parcelas.append({
            "parcela_numero": indice + 1,
            "valor": Decimal(centavos + (indice < resto)) / 100,
            "data_vencimento": primeiro_vencimento.replace(year=ano, month=mes, day=dia),
        })
    return parcelas


class ParcelamentoConflitante(ValueError):
    pass


class BoletoCompraSerializer(serializers.Serializer):
    idempotency_key = serializers.UUIDField()
    tipo = serializers.ChoiceField(choices=LancamentoFinanceiro.Tipo.choices)
    descricao = serializers.CharField(max_length=220)
    recebedor_nome = serializers.CharField(max_length=160)
    valor = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))
    parcela_numero = serializers.IntegerField(min_value=1, max_value=9999)
    total_boletos = serializers.IntegerField(min_value=1, max_value=9999)
    data_emissao = serializers.DateField(default=timezone.localdate)
    data_vencimento = serializers.DateField()
    observacoes = serializers.CharField(required=False, allow_blank=True, default="")
    codigo_barras = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")

    def validate_data_vencimento(self, value):
        return LancamentoFinanceiroSerializer().validate_data_vencimento(value)

    def validate_codigo_barras(self, value):
        return LancamentoFinanceiroSerializer().validate_codigo_barras(value)

    def validate(self, attrs):
        if attrs["parcela_numero"] > attrs["total_boletos"]:
            raise serializers.ValidationError({"parcela_numero": "O número deste boleto não pode ser maior que o total da compra."})
        return attrs


def registrar_boleto(dados):
    campos = {k: v for k, v in dados.items() if k != "idempotency_key"}
    assinatura = hashlib.sha256(json.dumps(campos, sort_keys=True, default=str, ensure_ascii=False).encode()).hexdigest()
    try:
        with transaction.atomic():
            grupo = ParcelamentoFinanceiro.objects.create(id=dados["idempotency_key"], assinatura=assinatura)
            boleto = LancamentoFinanceiro(parcelamento=grupo, **campos)
            boleto.full_clean()
            boleto.save()
        return boleto, False
    except IntegrityError:
        grupo = ParcelamentoFinanceiro.objects.filter(id=dados["idempotency_key"]).first()
        if grupo is None:
            raise
        if grupo.assinatura != assinatura:
            raise ParcelamentoConflitante("Esta solicitação já foi salva com outros dados. Confira a lista antes de salvar novamente.")
        return grupo.parcelas.get(), True


def criar_parcelamento(dados):
    conteudo = {k: v for k, v in dados.items() if k != "idempotency_key"}
    assinatura = hashlib.sha256(json.dumps(conteudo, sort_keys=True, default=str, ensure_ascii=False).encode()).hexdigest()
    chave = dados["idempotency_key"]
    try:
        with transaction.atomic():
            grupo = ParcelamentoFinanceiro.objects.create(id=chave, assinatura=assinatura)
            for parcela in calcular_parcelas(dados["valor_total"], dados["quantidade"], dados["primeiro_vencimento"]):
                lancamento = LancamentoFinanceiro(
                    parcelamento=grupo, **parcela,
                    tipo=dados["tipo"], descricao=dados["descricao"],
                    recebedor_nome=dados["recebedor_nome"], data_emissao=dados["data_emissao"],
                    observacoes=dados["observacoes"], codigo_barras=dados["codigo_barras"],
                )
                lancamento.full_clean()
                lancamento.save()
        return grupo, False
    except IntegrityError:
        grupo = ParcelamentoFinanceiro.objects.filter(id=chave).first()
        if grupo is None:
            raise
        if grupo.assinatura != assinatura:
            raise ParcelamentoConflitante("Esta solicitação já foi salva com outros dados. Atualize a lista antes de cadastrar novamente.")
        return grupo, True

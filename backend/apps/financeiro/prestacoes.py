"""Simulação SAC: fórmulas da PRESTAÇÃO CASE, sem lançamentos financeiros."""
from calendar import monthrange
from datetime import date
from decimal import Decimal, ROUND_HALF_UP, localcontext
from rest_framework import serializers, viewsets
from rest_framework.response import Response
from apps.accounts.access import verificar_acesso


class Parametros(serializers.Serializer):
    valor = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal('0.01'))
    entrada = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=0, default=0)
    juros_anual = serializers.DecimalField(max_digits=8, decimal_places=4, min_value=0, max_value=1000)
    parcelas = serializers.IntegerField(min_value=1, max_value=360)
    carencia = serializers.IntegerField(min_value=0, max_value=359, default=0)
    liberacao = serializers.DateField()
    primeiro_vencimento = serializers.DateField()
    periodicidade = serializers.ChoiceField(choices=['mensal', 'semestral', 'anual'])

    def validate(self, data):
        if data['entrada'] >= data['valor']:
            raise serializers.ValidationError('A entrada deve ser menor que o valor financiado da compra.')
        if data['primeiro_vencimento'] <= data['liberacao']:
            raise serializers.ValidationError('O primeiro vencimento deve ser posterior à liberação.')
        if data['parcelas'] + data['carencia'] > 360:
            raise serializers.ValidationError('A simulação suporta até 360 vencimentos, incluindo carência.')
        if data['primeiro_vencimento'].year + data['parcelas'] + data['carencia'] > 9999:
            raise serializers.ValidationError('Datas fora do intervalo suportado.')
        return data


def calcular(data):
    def dinheiro(v):
        return str(v.quantize(Decimal('.01'), rounding=ROUND_HALF_UP))
    with localcontext() as ctx:
        ctx.prec = 32
        financiado = data['valor'] - data['entrada']
        saldo = financiado
        amortizacao = financiado / data['parcelas']
        anterior = data['liberacao']
        primeira = data['primeiro_vencimento']
        passo = {'mensal': 1, 'semestral': 6, 'anual': 12}[data['periodicidade']]
        itens = []
        total = Decimal(0)
        total_juros = Decimal(0)
        quantidade = data['parcelas'] + data.get('carencia', 0)
        for i in range(quantidade):
            mes = primeira.year * 12 + primeira.month - 1 + i * passo
            ano, mes0 = divmod(mes, 12)
            vencimento = date(ano, mes0 + 1, min(primeira.day, monthrange(ano, mes0 + 1)[1]))
            dias = (vencimento - anterior).days
            juros = (saldo * ((1 + data['juros_anual'] / 100) ** (Decimal(dias) / 365) - 1)).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
            principal = Decimal(0) if i < data.get('carencia', 0) else saldo if i == quantidade - 1 else min(saldo, amortizacao.quantize(Decimal('.01'), rounding=ROUND_HALF_UP))
            saldo -= principal
            total += principal + juros
            total_juros += juros
            itens.append(dict(numero=i+1, vencimento=vencimento.isoformat(), dias=dias, amortizacao=dinheiro(principal), juros=dinheiro(juros), prestacao=dinheiro(principal+juros), saldo=dinheiro(saldo)))
            anterior = vencimento
        return dict(financiado=dinheiro(financiado), juros=dinheiro(total_juros), total_prestacoes=dinheiro(total), total_com_entrada=dinheiro(total+data['entrada']), media_prestacoes=dinheiro(total/quantidade), parcelas=itens,
                    criterio='SAC; taxa efetiva anual; dias corridos/365; valores arredondados por parcela. Na carência, paga-se somente juros. A média considera todos os vencimentos; não é prestação fixa. Sem tarifas, seguros ou ajuste de dias úteis.')


class PrestacoesViewSet(viewsets.ViewSet):
    def list(self, request):
        verificar_acesso(request.user, request.path, request.method)
        serializer = Parametros(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        try:
            return Response(calcular(serializer.validated_data))
        except (ArithmeticError, ValueError, OverflowError):
            raise serializers.ValidationError('Valores ou datas excedem a precisão suportada pela simulação.')

"""Resumo da titularidade de terceiros, sem somar versões ou saídas estornadas."""
from decimal import Decimal

from django.db.models import Prefetch
from django.http import HttpResponse
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.access import pode
from apps.accounts.views import NoStoreResponseMixin
from .models import EntradaProducaoTerceiro, MovimentoProducaoTerceiro


class FiltrosResumoSerializer(serializers.Serializer):
    terceiro = serializers.IntegerField(min_value=1, required=False)
    entrada = serializers.IntegerField(min_value=1, required=False)
    depositante = serializers.CharField(max_length=160, required=False, allow_blank=True)
    cultura = serializers.CharField(max_length=50, required=False, allow_blank=True)
    safra = serializers.CharField(max_length=20, required=False, allow_blank=True)


def resumir_terceiros(filtros):
    entradas = EntradaProducaoTerceiro.objects.select_related('terceiro')
    if filtros.get('terceiro'):
        entradas=entradas.filter(terceiro_id=filtros['terceiro'])
    if filtros.get('entrada'):
        entradas=entradas.filter(pk=filtros['entrada'])
    for campo in ("depositante", "cultura", "safra"):
        if filtros.get(campo):
            entradas = entradas.filter(**{f"{campo}__iexact": filtros[campo]})
    movimentos = MovimentoProducaoTerceiro.objects.select_related("estorno")
    entradas = entradas.prefetch_related(Prefetch("movimentos", queryset=movimentos))
    grupos = {}
    for entrada in entradas:
        chave = (('cadastro',entrada.terceiro_id) if entrada.terceiro_id else ('legado',entrada.pk), entrada.cultura.strip().casefold(), entrada.safra.strip().casefold())
        if chave not in grupos:
            grupos[chave] = {"terceiro":entrada.terceiro_id,"terceiro_codigo":entrada.terceiro.codigo if entrada.terceiro_id else '',"entrada_legada":None if entrada.terceiro_id else entrada.pk,"depositante": entrada.depositante, "cultura": entrada.cultura, "safra": entrada.safra, "recebimentos": 0, "cancelados": 0, "entradas_kg": Decimal(0), "saidas_kg": Decimal(0), "transferencias_kg": Decimal(0), "saldo_kg": Decimal(0)}
        grupo = grupos[chave]
        lista = list(entrada.movimentos.all())
        cancelada = any(m.tipo == "entrada" and hasattr(m, "estorno") for m in lista)
        grupo["cancelados" if cancelada else "recebimentos"] += 1
        if not cancelada:
            grupo["entradas_kg"] += entrada.peso_liquido_kg
        for movimento in lista:
            if movimento.tipo in ("saida", "transferencia") and not hasattr(movimento, "estorno"):
                grupo["saidas_kg"] += movimento.quantidade_kg
                if movimento.tipo == "transferencia":
                    grupo["transferencias_kg"] += movimento.quantidade_kg
        grupo["saldo_kg"] += entrada.saldo_kg
    campos = ("entradas_kg", "saidas_kg", "transferencias_kg", "saldo_kg")
    itens = sorted(grupos.values(), key=lambda g: (g["depositante"].casefold(), g["cultura"].casefold(), g["safra"]))
    totais = {campo: str(sum((g[campo] for g in itens), Decimal(0))) for campo in campos}
    for item in itens:
        for campo in campos:
            item[campo] = str(item[campo])
    return {"itens": itens, "totais": totais}


class ResumoTerceirosView(NoStoreResponseMixin, APIView):
    permission_classes = (IsAuthenticated,)
    excel = False

    def get(self, request):
        if not pode(request.user, "cargas", "consultar") or (self.excel and not pode(request.user, "cargas", "imprimir")):
            raise PermissionDenied("Sem permissão para consultar/exportar o resumo de terceiros.")
        serializer = FiltrosResumoSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        dados = resumir_terceiros(serializer.validated_data)
        if not self.excel:
            return Response(dados)
        from .romaneios_terceiros import gerar_resumo_excel
        resposta = HttpResponse(gerar_resumo_excel(dados, serializer.validated_data), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        resposta["Content-Disposition"] = 'attachment; filename="resumo-terceiros.xlsx"'
        return resposta

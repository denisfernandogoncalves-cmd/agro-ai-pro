from decimal import Decimal
from django.db.models import CharField, F, Func, Q, Sum, Value
from django.db.models.functions import Cast, Concat
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.accounts.access import pode
from apps.core.consulta_romaneios import (
    FiltrosRomaneiosSerializer, filtrar_periodo, normalizar_busca, pagina_romaneios, texto_sem_acentos,
)
from .models import CargaColhida, EntradaProducaoTerceiro, MovimentoProducaoTerceiro
from .serializers import CargaColhidaSerializer
from .terceiros import EntradaSerializer


class ProdutoresDoRomaneio(Func):
    """Busca nos nomes preservados no snapshot, iguais aos mostrados no romaneio."""
    template = "(SELECT string_agg((p->>'propriedade_nome') || ' / ' || COALESCE(p->>'cad_pro_numero', ''), ' · ') FROM jsonb_array_elements(COALESCE(%(expressions)s->'rateio_producao', '[]'::jsonb)) p)"
    output_field = CharField()


class FiltrosEntradaSerializer(FiltrosRomaneiosSerializer):
    origem = serializers.ChoiceField(choices=("", "propria", "terceiro"), default="", allow_blank=True)
    cultura = serializers.CharField(max_length=50, default="", allow_blank=True)
    terceiro = serializers.CharField(max_length=160, default="", allow_blank=True)


class ConsultaRomaneiosEntradaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not pode(request.user, "cargas", "consultar"):
            raise PermissionDenied("Sem permissão para consultar cargas.")
        entrada = FiltrosEntradaSerializer(data=request.query_params)
        entrada.is_valid(raise_exception=True)
        filtros = entrada.validated_data
        proprias = filtrar_periodo(CargaColhida.objects.all(), "data_colheita", filtros)
        terceiros = filtrar_periodo(EntradaProducaoTerceiro.objects.all(), "data_entrada", filtros)
        cancelados = MovimentoProducaoTerceiro.objects.filter(tipo="entrada", estorno__isnull=False).values("entrada_id")
        if not filtros["historico"]:
            proprias = proprias.filter(status="ativa")
            terceiros = terceiros.exclude(pk__in=cancelados)
        if filtros["cultura"]:
            proprias = proprias.filter(cultura=filtros["cultura"])
            terceiros = terceiros.filter(cultura=filtros["cultura"])
        if filtros["origem"] == "propria":
            terceiros = terceiros.none()
        if filtros["origem"] == "terceiro" or filtros["terceiro"]:
            proprias = proprias.none()
        if filtros["terceiro"]:
            terceiros = terceiros.alias(nome_busca=texto_sem_acentos(F("depositante"))).filter(nome_busca__contains=normalizar_busca(filtros["terceiro"]))
        busca = normalizar_busca(filtros["busca"])
        numero = busca.removeprefix("#")
        if numero.isdecimal():
            proprias = proprias.alias(numero_romaneio=Cast("pk", CharField()))
            filtro = Q(numero_romaneio=numero)
            if not busca.startswith("#"):
                filtro |= Q(contexto_colheita__rateio_producao__contains=[{"cad_pro_numero": numero}])
                filtro |= Q(contexto_colheita__rateio_producao__0__isnull=True, cad_pro__codigo=numero)
            proprias = proprias.filter(filtro)
            terceiros = terceiros.alias(numero_romaneio=Cast("pk", CharField())).filter(numero_romaneio=numero)
        elif busca:
            from django.db.models.functions import Coalesce
            nome = Coalesce(ProdutoresDoRomaneio(F("contexto_colheita")), Concat("propriedade__nome", Value(" / "), "cad_pro__codigo"))
            proprias = proprias.alias(texto_busca=texto_sem_acentos(Concat(nome, Value(" "), "placa", Value(" "), "cultura", Value(" "), "safra"))).filter(texto_busca__contains=busca)
            terceiros = terceiros.alias(texto_busca=texto_sem_acentos(Concat("depositante", Value(" "), "placa", Value(" "), "cultura", Value(" "), "safra"))).filter(texto_busca__contains=busca)
        peso_proprio = proprias.filter(status="ativa").aggregate(peso=Sum("peso_liquido_kg"))["peso"] or Decimal("0")
        peso_terceiro = terceiros.exclude(pk__in=cancelados).aggregate(peso=Sum("peso_liquido_kg"))["peso"] or Decimal("0")
        resposta, inicio = pagina_romaneios(proprias.count() + terceiros.count(), filtros)
        # União apenas de chaves: detalhes e históricos são carregados somente para a página.
        chaves_proprias = proprias.order_by().annotate(data_romaneio=F("data_colheita"), origem_romaneio=Value("propria")).values("id", "data_romaneio", "origem_romaneio")
        chaves_terceiros = terceiros.order_by().annotate(data_romaneio=F("data_entrada"), origem_romaneio=Value("terceiro")).values("id", "data_romaneio", "origem_romaneio")
        prefixo = "-" if filtros["ordem"] == "recentes" else ""
        chaves = list(chaves_proprias.union(chaves_terceiros, all=True).order_by(f"{prefixo}data_romaneio", f"{prefixo}id", "origem_romaneio")[inicio:inicio + resposta["por_pagina"]])
        cargas = CargaColhida.objects.filter(pk__in=[i["id"] for i in chaves if i["origem_romaneio"] == "propria"]).select_related("propriedade", "cad_pro", "armazem", "lote", "criado_por", "cancelada_por")
        entradas = EntradaProducaoTerceiro.objects.filter(pk__in=[i["id"] for i in chaves if i["origem_romaneio"] == "terceiro"]).select_related("armazem", "criado_por", "terceiro").prefetch_related("movimentos__criado_por", "movimentos__estorno")
        detalhes = {("propria", i.pk): CargaColhidaSerializer(i).data for i in cargas}
        detalhes.update({("terceiro", i.pk): EntradaSerializer(i).data for i in entradas})
        resposta["itens"] = [{"origem": i["origem_romaneio"], "registro": detalhes[(i["origem_romaneio"], i["id"])]} for i in chaves]
        resposta["peso_ativo_kg"] = str(peso_proprio + peso_terceiro)
        resposta["culturas"] = sorted(set(CargaColhida.objects.order_by().values_list("cultura", flat=True).distinct()).union(EntradaProducaoTerceiro.objects.order_by().values_list("cultura", flat=True).distinct()))
        return Response(resposta)

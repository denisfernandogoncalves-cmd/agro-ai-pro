from decimal import Decimal
from django.db.models import CharField, F, Q, Sum, Value
from django.db.models.functions import Cast, Concat
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.accounts.access import pode
from apps.core.consulta_romaneios import (
    FiltrosRomaneiosSerializer, filtrar_periodo, normalizar_busca, pagina_romaneios, texto_sem_acentos,
)
from .models import EntregaVendaGraos
from .serializers import EntregaVendaSerializer, VendaGraosSerializer


class VendaRomaneioSerializer(VendaGraosSerializer):
    class Meta(VendaGraosSerializer.Meta):
        fields = ("id", "numero_contrato", "cliente_nome", "excluida_em", "propriedade_nome",
                  "cad_pro_codigo", "cultura", "safra", "armazem_nome", "observacoes",
                  "contrato_preco_venda", "contrato_unidade_preco")


class ConsultaRomaneiosSaidaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not pode(request.user, "vendas", "consultar"):
            raise PermissionDenied("Sem permissão para consultar vendas.")
        entrada = FiltrosRomaneiosSerializer(data=request.query_params)
        entrada.is_valid(raise_exception=True)
        filtros = entrada.validated_data
        itens = filtrar_periodo(EntregaVendaGraos.objects.all(), "data_entrega", filtros)
        ativos = Q(cancelado_em__isnull=True, venda__excluida_em__isnull=True)
        if not filtros["historico"]:
            itens = itens.filter(ativos)
        busca = normalizar_busca(filtros["busca"])
        numero = busca.removeprefix("#")
        if numero.isdecimal():
            itens = itens.alias(numero_romaneio=Cast("pk", CharField()), numero_venda=Cast("venda_id", CharField())).filter(
                Q(numero_romaneio=numero) | Q(numero_venda=numero) | Q(nota_produtor=numero) |
                Q(nota_empresa=numero) | Q(venda__posicao__cad_pro__codigo=numero))
        elif busca:
            campos = ("venda__cliente_nome", "destino", "venda__numero_contrato", "venda__posicao__propriedade__nome",
                      "venda__posicao__cad_pro__codigo", "venda__posicao__cultura", "venda__posicao__safra",
                      "placa", "motorista", "nota_produtor", "nota_empresa")
            partes = [Value("Romaneio "), Cast("pk", CharField()), Value(" Venda #"), Cast("venda_id", CharField())]
            for campo in campos:
                partes.extend((Value(" "), F(campo)))
            itens = itens.alias(texto_busca=texto_sem_acentos(Concat(*partes))).filter(texto_busca__contains=busca)
        peso = itens.aggregate(peso=Sum("quantidade_kg", filter=ativos))["peso"] or Decimal("0")
        resposta, inicio = pagina_romaneios(itens.count(), filtros)
        prefixo = "-" if filtros["ordem"] == "recentes" else ""
        pagina = itens.select_related("venda__posicao__propriedade", "venda__posicao__cad_pro",
                                      "venda__posicao__armazem", "venda__contrato").order_by(
            f"{prefixo}data_entrega", f"{prefixo}id")[inicio:inicio + resposta["por_pagina"]]
        resposta["peso_ativo_kg"] = str(peso)
        resposta["itens"] = [{"venda": VendaRomaneioSerializer(item.venda).data,
                              "saida": EntregaVendaSerializer(item).data} for item in pagina]
        return Response(resposta)

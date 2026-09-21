"""Consulta de saldo atual e custo de aquisição, sem alterar o estoque."""
from decimal import Decimal, ROUND_HALF_UP

from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import MovimentacaoEstoque


class FiltrosDisponibilidade(serializers.Serializer):
    produto = serializers.IntegerField(min_value=1, required=False)
    fornecedor = serializers.IntegerField(min_value=1, required=False)
    data_inicio = serializers.DateField(required=False)
    data_fim = serializers.DateField(required=False)
    somente_disponivel = serializers.BooleanField(default=True)

    def validate(self, attrs):
        if attrs.get("data_inicio") and attrs.get("data_fim") and attrs["data_inicio"] > attrs["data_fim"]:
            raise serializers.ValidationError("A data inicial deve ser anterior ou igual à final.")
        return attrs


def disponibilidade_estoque(filtros):
    movimentos = MovimentacaoEstoque.objects.select_related(
        "lote__produto", "lote__fornecedor", "compra",
    ).order_by("lote_id", "data_movimento", "id")
    for campo in ("produto", "fornecedor"):
        if filtros.get(campo):
            movimentos = movimentos.filter(**{f"lote__{campo}_id": filtros[campo]})
    lotes = {}
    for movimento in movimentos:
        lote = movimento.lote
        item = lotes.setdefault(lote.pk, {
            "lote": lote, "entradas": Decimal(0), "saidas": Decimal(0),
            "valor": Decimal(0), "datas": set(), "custo_completo": True,
        })
        if movimento.tipo == "saida":
            item["saidas"] += movimento.quantidade
        else:
            item["entradas"] += movimento.quantidade
            item["datas"].add(movimento.data_movimento)
            compra = getattr(movimento, "compra", None)
            if compra is not None:
                item["valor"] += compra.valor_total
            elif movimento.custo_unitario is not None:
                item["valor"] += movimento.quantidade * movimento.custo_unitario
            else:
                item["custo_completo"] = False
    grupos = {}
    for item in lotes.values():
        datas = sorted(item["datas"])
        if not datas:
            continue
        # Filtro seleciona compras; saídas posteriores sempre compõem o saldo atual.
        if not any((not filtros.get("data_inicio") or d >= filtros["data_inicio"])
                   and (not filtros.get("data_fim") or d <= filtros["data_fim"]) for d in datas):
            continue
        lote = item["lote"]
        data = datas[0] if len(datas) == 1 else None
        chave = (lote.produto_id, lote.fornecedor_id, data)
        grupo = grupos.setdefault(chave, {
            "produto_id": lote.produto_id, "produto": lote.produto.nome,
            "fornecedor_id": lote.fornecedor_id,
            "fornecedor": lote.fornecedor.nome if lote.fornecedor else "Fornecedor não informado",
            "unidade": lote.produto.unidade, "data_compra": data,
            "quantidade_comprada": Decimal(0), "quantidade_saida": Decimal(0),
            "disponivel": Decimal(0), "valor_aquisicao": Decimal(0),
            "custo_completo": True, "lotes": [],
        })
        grupo["quantidade_comprada"] += item["entradas"]
        grupo["quantidade_saida"] += item["saidas"]
        grupo["disponivel"] += item["entradas"] - item["saidas"]
        grupo["valor_aquisicao"] += item["valor"]
        grupo["custo_completo"] &= item["custo_completo"]
        grupo["lotes"].append({"id": lote.pk, "codigo": lote.codigo, "datas_entrada": datas})
    resultado = []
    totais = {}
    for grupo in grupos.values():
        if filtros.get("somente_disponivel", True) and grupo["disponivel"] <= 0:
            continue
        chave_resumo = (grupo["produto_id"], grupo["fornecedor_id"])
        resumo = totais.setdefault(chave_resumo, {
            "produto_id": grupo["produto_id"], "produto": grupo["produto"],
            "fornecedor_id": grupo["fornecedor_id"], "fornecedor": grupo["fornecedor"],
            "unidade": grupo["unidade"], "comprado": Decimal(0),
            "disponivel": Decimal(0), "valor": Decimal(0), "completo": True,
        })
        resumo["comprado"] += grupo["quantidade_comprada"]
        resumo["disponivel"] += grupo["disponivel"]
        resumo["valor"] += grupo["valor_aquisicao"]
        resumo["completo"] &= grupo["custo_completo"]
        completo = grupo.pop("custo_completo")
        grupo["preco_medio"] = str((grupo["valor_aquisicao"] / grupo["quantidade_comprada"]).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)) if completo else None
        grupo["valor_aquisicao"] = str(grupo["valor_aquisicao"].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)) if completo else None
        for campo in ("quantidade_comprada", "quantidade_saida", "disponivel"):
            grupo[campo] = str(grupo[campo].quantize(Decimal("0.001")))
        resultado.append(grupo)
    resumo_final = []
    for resumo in totais.values():
        comprado, valor, completo = resumo.pop("comprado"), resumo.pop("valor"), resumo.pop("completo")
        resumo["disponivel"] = str(resumo["disponivel"].quantize(Decimal("0.001")))
        resumo["preco_medio"] = str((valor / comprado).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)) if completo else None
        resumo_final.append(resumo)
    return {
        "itens": sorted(resultado, key=lambda g: (g["produto"], g["fornecedor"], str(g["data_compra"] or ""))),
        "resumo": sorted(resumo_final, key=lambda g: (g["produto"], g["fornecedor"])),
    }


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def disponibilidade(request):
    filtros = FiltrosDisponibilidade(data=request.query_params)
    filtros.is_valid(raise_exception=True)
    return Response(disponibilidade_estoque(filtros.validated_data))

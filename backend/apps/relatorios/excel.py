from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from rest_framework import permissions, serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView
from apps.accounts.access import pode
from apps.accounts.views import NoStoreResponseMixin
from apps.core.excel import PlanilhaExportacao, consulta_consistente
from .serializers import FiltrosRelatorioOperacionalSerializer
from .selectors import selecionar_relatorio_operacional


def tipo_valor(chave, valor):
    campo = chave.rsplit(".", 1)[-1]
    if campo == "id" or campo.endswith("_id") or campo in {"cad_pro", "cad_pro_codigo", "codigo"}:
        return str(valor) if valor is not None else None
    if isinstance(valor, str) and (campo.endswith(("_kg", "_hectares", "_alqueires", "_percentual")) or campo.startswith(("valor", "custo", "quantidade", "sacas_", "media_"))):
        try: return Decimal(valor)
        except InvalidOperation: return valor
    if isinstance(valor,str) and (campo.startswith("data") or campo.endswith("_em")):
        try: return datetime.fromisoformat(valor) if "T" in valor or " " in valor else date.fromisoformat(valor)
        except ValueError: return valor
    return valor


def achatar(item, prefixo=""):
    resultado = {}
    for chave, valor in item.items():
        nome = f"{prefixo}{chave}"
        if isinstance(valor, dict):
            resultado.update(achatar(valor, nome + "."))
        else:
            resultado[nome] = tipo_valor(nome, valor)
    return resultado


class RelatorioExcelView(NoStoreResponseMixin, APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        if not pode(request.user, "relatorios", "consultar") or not pode(request.user, "relatorios", "imprimir"):
            raise PermissionDenied()
        serializer = FiltrosRelatorioOperacionalSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        filtros = {**serializer.validated_data, "pagina": 1, "por_pagina": 100000}
        with consulta_consistente():
            dados = selecionar_relatorio_operacional(**filtros)
            if dados["dados"]["total"] > 100000:
                raise serializers.ValidationError("Mais de 100.000 resultados. Reduza o período ou os filtros para exportar todas as linhas.")
            planilha = PlanilhaExportacao(f"Relatório {dados['secao']}: todos os resultados dos filtros aplicados.")
            planilha.adicionar("Filtros", ["Campo", "Valor"], dados["filtros"].items())
            itens = [achatar(item) for item in dados["dados"]["resultados"]]
            colunas = list(dict.fromkeys(chave for item in itens for chave in item)) or ["Resultado"]
            planilha.adicionar("Resultados", colunas, ([item.get(c) for c in colunas] for item in itens))
            planilha.adicionar("Totais", ["Indicador", "Valor"], ((c, tipo_valor(c, v)) for c,v in dados["totais"].items()))
            if dados["secao"] == "producao_propriedade":
                planilha.adicionar("Totais de produção", ["Indicador", "Valor"], ((c, tipo_valor(c, v)) for c,v in dados["totais_producao_propriedade"].items()))
        return planilha.resposta("agro-relatorio")

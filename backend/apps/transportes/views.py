import csv
import io
from decimal import Decimal, ROUND_HALF_UP

from django.http import HttpResponse

from django.db.models.deletion import ProtectedError
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from .importacao import importar, ler_planilha
from .models import Caminhao, LancamentoTransporte, RemuneracaoMotorista
from .relatorios import relatorio, selecionar
from .serializers import CaminhaoSerializer, LancamentoSerializer, RemuneracaoSerializer


class Paginacao(PageNumberPagination):
    page_size = 30


class CaminhaoViewSet(viewsets.ModelViewSet):
    queryset = Caminhao.objects.all()
    serializer_class = CaminhaoSerializer

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError:
            raise ValidationError("Caminhão com histórico não pode ser excluído. Desative-o no cadastro.")


class LancamentoViewSet(viewsets.ModelViewSet):
    serializer_class = LancamentoSerializer
    pagination_class = Paginacao

    def get_queryset(self):
        return selecionar(LancamentoTransporte, self.request.query_params)

    @action(detail=False, methods=["get"])
    def relatorio(self, request):
        return Response(relatorio(request.query_params))

    @action(detail=False, methods=["get"])
    def exportar(self, request):
        resultado = relatorio(request.query_params)
        saida = io.StringIO()
        escritor = csv.writer(saida, delimiter=";")
        def seguro(valor):
            texto = str(valor)
            return "'" + texto if texto.lstrip().startswith(("=", "+", "-", "@")) and not isinstance(valor, Decimal) else texto
        escritor.writerow(["AGRO-AI-PRO — Transportes"])
        escritor.writerow(["Filtros", *[f"{k}: {v}" for k, v in request.query_params.items() if k != "page"]])
        escritor.writerow([resultado["criterio_remuneracao"]])
        for titulo, grupos in (("Total", [resultado["resumo"]]), ("Ranking por placa", resultado["por_placa"]), ("Ranking por motorista", resultado["por_motorista"]), ("Resultado mensal", resultado["por_mes"])):
            escritor.writerow([titulo])
            escritor.writerow(["Identificação", "Receita", "Despesas operacionais", "Salário", "Comissão", "Despesas totais", "Saldo", "Margem %"])
            for grupo in grupos:
                escritor.writerow([seguro(grupo["nome"]), *[(grupo[k] or "").replace(".", ",") for k in ("receita", "despesas_operacionais", "salario", "comissao", "despesas", "saldo", "margem")]])
        escritor.writerow(["Todos os lançamentos filtrados"])
        escritor.writerow(["Data", "Placa", "Motorista", "Tipo", "Descrição", "Origem/destino/local", "Nota", "Quantidade", "Unidade", "Valor unitário", "Total"])
        for item in selecionar(LancamentoTransporte, request.query_params):
            escritor.writerow([str(item.data), seguro(item.caminhao.placa), seguro(item.motorista), item.tipo, seguro(item.descricao), seguro(item.local), seguro(item.nota), str(item.quantidade).replace(".", ","), seguro(item.unidade), str(item.valor_unitario).replace(".", ","), str(item.total).replace(".", ",")])
        resposta = HttpResponse("\ufeff" + saida.getvalue(), content_type="text/csv; charset=utf-8")
        resposta["Content-Disposition"] = 'attachment; filename="transportes.csv"'
        return resposta

    @action(detail=False, methods=["post"])
    def previa(self, request):
        dados = ler_planilha(request.FILES.get("arquivo"))
        receita = sum(((Decimal(i["quantidade"]) * Decimal(i["valor_unitario"])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) for i in dados["lancamentos"] if i["tipo"] == "receita"), Decimal(0))
        despesa = sum(((Decimal(i["quantidade"]) * Decimal(i["valor_unitario"])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) for i in dados["lancamentos"] if i["tipo"] == "despesa"), Decimal(0))
        return Response(dict(veiculos=dados["veiculos"], quantidade=len(dados["lancamentos"]), duplicados=dados["duplicados"], receitas=str(receita), despesas_operacionais=str(despesa), remuneracoes=dados["remuneracoes"], amostra=dados["lancamentos"][:10], aviso="Cada lançamento é arredondado a centavos. Salários e percentuais são lidos da planilha. A comissão é calculada sobre receitas menos despesas de AREIA e PEDRA. Reimportar não substitui registros existentes."))

    @action(detail=False, methods=["post"])
    def importar(self, request):
        return Response(importar(ler_planilha(request.FILES.get("arquivo"))))


class RemuneracaoViewSet(viewsets.ModelViewSet):
    serializer_class = RemuneracaoSerializer
    pagination_class = Paginacao

    @action(detail=False, methods=["get"])
    def calculo(self, request):
        campos = RemuneracaoSerializer().fields
        dados = {k: campos[k].run_validation(request.query_params.get(k)) for k in ("caminhao", "motorista", "competencia", "comissao_percentual")}
        if dados["competencia"].day != 1 or dados["comissao_percentual"] is None:
            raise ValidationError("Informe competência e percentual válidos.")
        base_por_aba = False
        if request.query_params.get("id"):
            existente = self.get_queryset().filter(pk=request.query_params["id"]).first()
            if existente and existente.caminhao_id == dados["caminhao"].pk and existente.motorista == dados["motorista"] and existente.competencia == dados["competencia"]:
                base_por_aba = existente.base_por_aba
        item = RemuneracaoMotorista(**dados, base_por_aba=base_por_aba)
        return Response(dict(base_comissao=str(item.base_comissao), comissao=str(item.valor_comissao)))

    def get_queryset(self):
        # Cadastro filtra competência como mês; relatório aplica fechamento no último dia.
        params = {k: v for k, v in self.request.query_params.items() if k not in ("data_inicio", "data_fim")}
        qs = selecionar(RemuneracaoMotorista, params)
        if self.request.query_params.get("competencia"):
            campo = self.serializer_class().fields["competencia"]
            qs = qs.filter(competencia=campo.run_validation(self.request.query_params["competencia"]))
        return qs

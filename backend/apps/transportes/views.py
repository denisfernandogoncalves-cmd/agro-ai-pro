import csv
import io
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from django.http import HttpResponse

from django.db.models.deletion import ProtectedError
from django.db import transaction
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from apps.accounts.access import verificar_acesso
from apps.core.correcoes import CorrecaoHistoricoMixin, EdicaoVersionadaMixin

from .importacao import importar, ler_planilha
from .models import Caminhao, LancamentoTransporte, RemuneracaoMotorista
from .relatorios import relatorio, selecionar
from .ranking import rankings
from .serializers import CaminhaoSerializer, LancamentoSerializer, RemuneracaoSerializer


class Paginacao(PageNumberPagination):
    page_size = 30


class CaminhaoViewSet(EdicaoVersionadaMixin, viewsets.ModelViewSet):
    queryset = Caminhao.objects.all()
    serializer_class = CaminhaoSerializer

    @action(detail=True, methods=["delete"], url_path="motorista")
    def desvincular_motorista(self, request, pk=None):
        verificar_acesso(request.user, request.path, request.method)
        with transaction.atomic():
            instance = self.get_queryset().select_for_update().get(pk=self.get_object().pk)
            if request.data.get("motorista_original") != instance.motorista:
                return Response({"detail": "O motorista foi alterado. Atualize a consulta antes de desvincular."}, status=409)
            instance.motorista = ""
            instance.save(update_fields=["motorista"])
        return Response(self.get_serializer(instance).data)

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError:
            raise ValidationError("Caminhão com histórico não pode ser excluído. Desative-o no cadastro.")


class LancamentoViewSet(EdicaoVersionadaMixin, viewsets.ModelViewSet):
    serializer_class = LancamentoSerializer
    pagination_class = Paginacao

    @action(detail=False, methods=["get"], url_path="preco-silo")
    def preco_silo(self, request):
        from .diesel import ultima_compra_diesel
        campos = LancamentoSerializer().fields
        data = campos["data"].run_validation(request.query_params.get("data"))
        tipo = campos["tipo_diesel"].run_validation(request.query_params.get("tipo_diesel"))
        compra = ultima_compra_diesel(data, tipo)
        return Response({"compra": compra.pk, "data_compra": str(compra.data), "valor_unitario": str(compra.valor_unitario), "tipo_diesel": compra.tipo})

    def get_queryset(self):
        return selecionar(LancamentoTransporte, self.request.query_params).select_related("compra_diesel")

    @action(detail=False, methods=["get"])
    def relatorio(self, request):
        verificar_acesso(request.user, request.path, request.method)
        resultado = relatorio(request.query_params)
        resultado.update(rankings(resultado, request.query_params, request.user))
        return Response(resultado)

    @action(detail=False, methods=["get"])
    def exportar(self, request):
        verificar_acesso(request.user, request.path, request.method)
        resultado = relatorio(request.query_params)
        resultado.update(rankings(resultado, request.query_params, request.user))
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
        escritor.writerow([resultado["criterio_ranking"]])
        for titulo, grupos in (("Ranking financeiro por resultado", resultado["ranking_financeiro"]), ("Ranking de eficiencia por margem", resultado["ranking_eficiencia"])):
            escritor.writerow([titulo])
            escritor.writerow(["Posicao", "Motorista", "Receita", "Custos totais", "Resultado", "Margem %"])
            for posicao, grupo in enumerate(grupos, 1):
                escritor.writerow([posicao, seguro(grupo["nome"]), *[(grupo[k] or "").replace(".", ",") for k in ("receita", "despesas", "saldo", "margem")]])
        escritor.writerow(["Ranking operacional por carga media documentada"])
        escritor.writerow(["Posicao", "Motorista", "Documentos", "Toneladas", "Toneladas por documento"])
        for posicao, grupo in enumerate(resultado["ranking_operacional"], 1):
            escritor.writerow([posicao, seguro(grupo["nome"]), grupo["documentos"], grupo["toneladas"].replace(".", ","), grupo["toneladas_por_documento"].replace(".", ",")])
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


class RemuneracaoViewSet(CorrecaoHistoricoMixin, EdicaoVersionadaMixin, viewsets.ModelViewSet):
    modulo_correcao = "transportes"
    campos_correcao = ("motorista", "competencia", "salario", "comissao_percentual", "comissao_manual", "observacoes")

    def corrigir_historico(self, instancia, dados, request):
        if instancia.fretes_conferidos.exists() and any(nome in dados and dados[nome] != getattr(instancia, nome) for nome in ("motorista", "competencia")):
            raise ValidationError("A remuneração possui fretes. Preserve motorista e competência ou cancele os fretes vinculados antes de corrigir o vínculo.")
        percentual = dados.get("comissao_percentual", instancia.comissao_percentual)
        if percentual is not None and "comissao_manual" in dados and dados["comissao_manual"] != instancia.comissao:
            raise ValidationError("A comissão usa o percentual cadastrado. Para valor manual, deixe o percentual vazio.")
        if dados.get("competencia", instancia.competencia).day != 1:
            raise ValidationError("A competência deve ser o primeiro dia do mês.")
        if any(nome in dados and dados[nome] != getattr(instancia, nome) for nome in ("motorista", "competencia")):
            instancia.base_por_aba = False
        for nome, valor in dados.items():
            setattr(instancia, "comissao" if nome == "comissao_manual" else nome, valor)
        instancia.full_clean()
        instancia.save()
    serializer_class = RemuneracaoSerializer
    pagination_class = Paginacao

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError:
            raise ValidationError("Remuneração com fretes conferidos não pode ser excluída.")

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

    @action(detail=False, methods=["get"])
    def imprimir(self, request):
        verificar_acesso(request.user, request.path, request.method)
        mes = request.query_params.get("mes", "")
        try:
            competencia = date.fromisoformat(mes + "-01")
            if len(mes) != 7:
                raise ValueError
        except (ValueError, TypeError):
            raise ValidationError({"mes": "Escolha um mês válido (AAAA-MM)."})
        grupos = {}
        registros = self.get_queryset().filter(competencia=competencia)
        for item in self.get_serializer(registros, many=True).data:
            chave = item["motorista"].strip().casefold()
            grupo = grupos.setdefault(chave, {"motorista": item["motorista"], "competencia": mes,
                "salario": Decimal(0), "comissao": Decimal(0), "comissao_fretes": Decimal(0), "itens": []})
            grupo["salario"] += Decimal(item["salario"])
            grupo["comissao"] += Decimal(item["comissao"])
            grupo["comissao_fretes"] += Decimal(item["comissao_fretes"])
            grupo["itens"].append(item)
        resultado = []
        for chave in sorted(grupos):
            grupo = grupos[chave]
            from .models import PagamentoEmprestimo
            pagamentos = PagamentoEmprestimo.objects.filter(remuneracao_id__in=[i["id"] for i in grupo["itens"]], estornado_em__isnull=True)
            grupo["emprestimos_pagos"] = [{"id": p.id, "emprestimo": p.emprestimo_id, "data": p.data.isoformat(), "valor": str(p.valor)} for p in pagamentos]
            desconto = sum((Decimal(p["valor"]) for p in grupo["emprestimos_pagos"]), Decimal(0))
            grupo["desconto_emprestimos"] = str(desconto)
            grupo["total_liquido"] = str(grupo["salario"] + grupo["comissao"] - desconto)
            grupo["total"] = str(grupo["salario"] + grupo["comissao"])
            grupo["comissao_fretes"] = str(grupo["comissao_fretes"])
            grupo["salario"] = str(grupo["salario"])
            grupo["comissao"] = str(grupo["comissao"])
            resultado.append(grupo)
        return Response(resultado)

    def get_queryset(self):
        # Cadastro filtra competência como mês; relatório aplica fechamento no último dia.
        params = {k: v for k, v in self.request.query_params.items() if k not in ("data_inicio", "data_fim")}
        qs = selecionar(RemuneracaoMotorista, params)
        if self.request.query_params.get("competencia"):
            campo = self.serializer_class().fields["competencia"]
            qs = qs.filter(competencia=campo.run_validation(self.request.query_params["competencia"]))
        return qs

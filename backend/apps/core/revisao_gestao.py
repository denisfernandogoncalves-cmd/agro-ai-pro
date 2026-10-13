from decimal import Decimal
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F, Q, Sum, Value, Window
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.accounts.access import pode
from apps.accounts.views import NoStoreResponseMixin
from apps.graos.models import MovimentacaoGraos
from apps.producao.models import OperacaoAgricola
from apps.relatorios.selectors import _produtividade, _producao_por_propriedade_cad_pro, _totais_producao_propriedade
from .models import ChecklistSafra, RegistroAlteracao

ETAPAS = ("saldo", "contagem", "vendas", "pendencias", "financeiro")


class ChecklistEntrada(serializers.Serializer):
    safra = serializers.CharField(max_length=20)
    etapas = serializers.ListField(child=serializers.ChoiceField(choices=ETAPAS), max_length=5)
    observacoes = serializers.CharField(max_length=2000, allow_blank=True, default="")
    versao = serializers.IntegerField(min_value=0)

    def validate_etapas(self, valor):
        if len(valor) != len(set(valor)):
            raise serializers.ValidationError("Uma etapa só pode ser marcada uma vez.")
        return valor


def checklist_dados(obj):
    return {"safra": obj.safra, "etapas": obj.etapas, "observacoes": obj.observacoes,
            "versao": obj.versao, "responsavel": obj.usuario.username, "atualizado_em": obj.atualizado_em}


class ChecklistSafraView(NoStoreResponseMixin, APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        if not pode(request.user, "relatorios", "consultar"):
            raise PermissionDenied()
        safra = serializers.CharField(max_length=20).run_validation(request.query_params.get("safra", ""))
        obj = ChecklistSafra.objects.filter(usuario=request.user, safra=safra).first()
        if not obj:
            return Response({"safra": safra, "etapas": [], "observacoes": "", "versao": 0, "responsavel": request.user.username, "atualizado_em": None, "historico": []})
        historico = RegistroAlteracao.objects.filter(entidade="checklist_safra", registro_id=str(obj.pk), usuario=request.user).order_by("-id")[:25]
        return Response({**checklist_dados(obj), "historico": list(historico.values("usuario_nome", "criado_em", "alteracoes"))})

    def put(self, request):
        entrada = ChecklistEntrada(data=request.data)
        entrada.is_valid(raise_exception=True)
        d = entrada.validated_data
        if not pode(request.user, "relatorios", "cadastrar" if d["versao"] == 0 else "editar"):
            raise PermissionDenied()
        with transaction.atomic():
            # Serializa criação concorrente para o mesmo usuário sem sobrescrever revisão.
            get_user_model().objects.select_for_update().get(pk=request.user.pk)
            obj = ChecklistSafra.objects.select_for_update().filter(usuario=request.user, safra=d["safra"]).first()
            if (obj.versao if obj else 0) != d["versao"]:
                return Response({"detail": "O checklist mudou. Carregue a revisão antes de salvar."}, status=409)
            antes = checklist_dados(obj) if obj else None
            if obj:
                obj.etapas = d["etapas"]
                obj.observacoes = d["observacoes"]
                obj.versao += 1
                obj.save()
            else:
                obj = ChecklistSafra.objects.create(usuario=request.user, safra=d["safra"], etapas=d["etapas"], observacoes=d["observacoes"])
            RegistroAlteracao.objects.create(usuario=request.user, usuario_nome=request.user.username, modulo="relatorios", entidade="checklist_safra", registro_id=str(obj.pk),
                acao="editar" if antes else "cadastrar", alteracoes={"antes": {**antes, "atualizado_em": str(antes["atualizado_em"])} if antes else None,
                    "depois": {**checklist_dados(obj), "atualizado_em": str(obj.atualizado_em)}})
        return Response(checklist_dados(obj))


class FiltrosExtrato(serializers.Serializer):
    propriedade = serializers.IntegerField(min_value=1, required=True)
    cad_pro = serializers.UUIDField(required=False)
    cultura = serializers.CharField(max_length=50, required=False, allow_blank=True)
    safra = serializers.CharField(max_length=20, required=False, allow_blank=True)
    inicio = serializers.DateField()
    fim = serializers.DateField()
    pagina = serializers.IntegerField(min_value=1, max_value=1000000, default=1)

    def validate(self, dados):
        if dados["inicio"] > dados["fim"]:
            raise serializers.ValidationError("A data final deve ser igual ou posterior à inicial.")
        return dados


def extrato_cadpro(d):
    qs = MovimentacaoGraos.objects.filter(posicao__propriedade_id=d["propriedade"])
    for campo in ("cad_pro", "cultura", "safra"):
        if d.get(campo):
            qs = qs.filter(**{f"posicao__{campo}": d[campo]})
    zero = Decimal("0.000")
    saldo_inicial = qs.filter(data_movimento__lt=d["inicio"]).aggregate(v=Sum("delta_fisico_kg"))["v"] or zero
    periodo = qs.filter(data_movimento__range=(d["inicio"], d["fim"]))
    total = periodo.count()
    delta = periodo.aggregate(v=Sum("delta_fisico_kg"))["v"] or zero
    ordenacao = [F("data_movimento").asc(), F("id").asc()]
    linhas = periodo.annotate(saldo_extrato=Window(Sum("delta_fisico_kg"), order_by=ordenacao) + Value(saldo_inicial)).select_related("origem", "estorno_de__origem", "posicao__cad_pro", "posicao__armazem").order_by("data_movimento", "id")
    inicio = (d["pagina"] - 1) * 25
    itens = []
    for m in linhas[inicio:inicio + 25]:
        externo = m.origem.metadados.get("tipo") == "transferencia_terceiro" or bool(m.estorno_de and m.estorno_de.origem.metadados.get("tipo") == "transferencia_terceiro")
        itens.append({"id": m.pk, "data": m.data_movimento, "operacao": m.operacao,
                      "origem": "Estoque externo de terceiros" if externo else m.get_operacao_display(),
                      "origem_externa": externo, "cad_pro": m.posicao.cad_pro.codigo, "armazem": m.posicao.armazem.nome,
                      "delta_kg": m.delta_fisico_kg, "comprometido_kg": m.delta_comprometido_kg,
                      "saldo_kg": m.saldo_extrato, "referencia": m.referencia_externa})
    return {"resultados": itens, "total": total, "pagina": d["pagina"], "total_paginas": (total + 24) // 25,
            "saldo_inicial_kg": saldo_inicial, "variacao_kg": delta, "saldo_final_kg": saldo_inicial + delta, "gerado_em": timezone.now()}


class ExtratoCadproView(NoStoreResponseMixin, APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        if not pode(request.user, "producao-saldos", "consultar"):
            raise PermissionDenied()
        entrada = FiltrosExtrato(data=request.query_params)
        entrada.is_valid(raise_exception=True)
        return Response(extrato_cadpro(entrada.validated_data))


class FiltrosComparacao(serializers.Serializer):
    safras = serializers.ListField(child=serializers.CharField(max_length=20), min_length=2, max_length=4)
    cultura = serializers.CharField(max_length=50)
    propriedade = serializers.IntegerField(min_value=1, required=False)

    def validate_safras(self, valor):
        if len(valor) != len(set(valor)):
            raise serializers.ValidationError("Informe safras diferentes.")
        return valor


def comparar_safras(d, mostrar_custo):
    resultados = []
    for safra in d["safras"]:
        filtros = {"safra": safra, "cultura": d["cultura"], **({"propriedade": d["propriedade"]} if d.get("propriedade") else {})}
        producao = _totais_producao_propriedade(_producao_por_propriedade_cad_pro(_produtividade(filtros)))
        custos = OperacaoAgricola.objects.filter(talhao__safra=safra, talhao__cultura_atual__iexact=d["cultura"]).exclude(status="cancelada")
        if d.get("propriedade"):
            custos = custos.filter(talhao__propriedade_id=d["propriedade"])
        custo = custos.aggregate(v=Sum("custo_realizado"))["v"] if mostrar_custo else None
        resultados.append({"safra": safra, **producao, "custo_operacoes": custo,
                           "operacoes_sem_custo": custos.filter(custo_realizado__isnull=True).count() if mostrar_custo else None})
    return resultados


class ComparacaoSafrasView(NoStoreResponseMixin, APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        if not pode(request.user, "relatorios", "consultar"):
            raise PermissionDenied()
        dados = request.query_params.dict()
        dados["safras"] = request.query_params.getlist("safra")
        entrada = FiltrosComparacao(data=dados)
        entrada.is_valid(raise_exception=True)
        return Response({"resultados": comparar_safras(entrada.validated_data, pode(request.user, "operacoes", "consultar")),
                         "custo_autorizado": pode(request.user, "operacoes", "consultar"), "gerado_em": timezone.now()})

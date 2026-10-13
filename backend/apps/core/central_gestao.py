"""Consultas de apoio, sem alteração de saldos ou registros operacionais."""
from django import get_version
from django.db import connection
from django.db.models import CharField, DateField, F, Q, Value, DecimalField, Sum, Case, When, Exists, OuterRef
from django.db.models.functions import Cast, Coalesce
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.accounts.access import pode, permissoes_do_usuario
from apps.accounts.views import NoStoreResponseMixin
from apps.financeiro.models import LancamentoFinanceiro
from apps.graos.models import CargaColhida, EntradaProducaoTerceiro, MovimentoProducaoTerceiro
from apps.vendas.models import EntregaVendaGraos
from .anexos import ALVOS
from .backup_status import situacao_backup
from .models import AnexoLancamento


class FiltrosGestao(serializers.Serializer):
    pagina = serializers.IntegerField(min_value=1, default=1)
    busca = serializers.CharField(max_length=160, required=False, default="")
    inicio = serializers.DateField(required=False)
    fim = serializers.DateField(required=False)
    tipo = serializers.ChoiceField(choices=("", "carga", "terceiro", "retirada", "transferencia", "entrega", "anexo"), default="")
    somente_diferencas = serializers.BooleanField(default=True)

    def validate(self, dados):
        if dados.get("inicio") and dados.get("fim") and dados["inicio"] > dados["fim"]:
            raise serializers.ValidationError("A data final deve ser igual ou posterior à inicial.")
        return dados


class DiagnosticoView(NoStoreResponseMixin, APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        # Não devolve credenciais, caminhos privados ou mensagens do driver.
        banco = False
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                banco = cursor.fetchone()[0] == 1
        except Exception:
            pass
        dados = {"conexao": "ok", "banco": "ok" if banco else "indisponivel",
                 "api": "v1", "django": get_version(), "verificado_em": timezone.now()}
        if request.user.is_staff:
            dados["backup"] = situacao_backup()
        return Response(dados)


class DocumentosView(NoStoreResponseMixin, APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        entrada = FiltrosGestao(data=request.query_params)
        entrada.is_valid(raise_exception=True)
        filtros = entrada.validated_data
        fontes = []
        permissoes = permissoes_do_usuario(request.user)
        def autorizado(modulo, acao):
            return acao in permissoes.get(modulo, [])

        def incluir(qs, tipo, data, nome, modulo, extras=(), situacao=None, referencia=None, download=True):
            if not autorizado(modulo, "consultar") or filtros["tipo"] not in ("", tipo):
                return
            if tipo == "transferencia" and not autorizado("transferencias", "consultar"):
                return
            termo = filtros["busca"].strip()
            if termo:
                busca = Q(**{f"{nome}__icontains": termo})
                for campo in extras:
                    busca |= Q(**{f"{campo}__icontains": termo})
                if termo.lstrip("#").isdigit():
                    busca |= Q(pk=int(termo.lstrip("#")))
                qs = qs.filter(busca)
            if filtros.get("inicio"):
                qs = qs.filter(**{f"{data}__date__gte" if data == "criado_em" else f"{data}__gte": filtros["inicio"]})
            if filtros.get("fim"):
                qs = qs.filter(**{f"{data}__date__lte" if data == "criado_em" else f"{data}__lte": filtros["fim"]})
            imprimir = download and autorizado(modulo, "imprimir")
            if tipo == "transferencia":
                imprimir = imprimir and autorizado("transferencias", "imprimir")
            fontes.append(qs.order_by().annotate(
                doc_tipo=Value(tipo, output_field=CharField()), doc_numero=F("pk"),
                doc_data=Cast(F(data), DateField()), doc_nome=Cast(F(nome), CharField()),
                doc_situacao=Cast(situacao or Value("Consultar histórico e estornos"), CharField()),
                doc_referencia=Cast(referencia or Value(""), CharField()), doc_imprimir=Value(imprimir),
            ).values("doc_tipo", "doc_numero", "doc_data", "doc_nome", "doc_situacao", "doc_referencia", "doc_imprimir"))

        incluir(CargaColhida.objects.all(), "carga", "data_colheita", "propriedade__nome", "cargas", ("placa", "cad_pro__codigo", "propriedade__proprietario", "motorista"), F("status"))
        cancelado = MovimentoProducaoTerceiro.objects.filter(entrada_id=OuterRef("pk"), tipo="entrada", estorno__isnull=False)
        terceiros = EntradaProducaoTerceiro.objects.annotate(doc_cancelado=Exists(cancelado))
        incluir(terceiros, "terceiro", "data_entrada", "depositante", "cargas", ("placa", "cad_pro", "propriedade_origem"),
                Case(When(doc_cancelado=True, then=Value("Cancelado")), default=Value("Ativo")))
        for tipo in ("saida", "transferencia"):
            incluir(MovimentoProducaoTerceiro.objects.filter(tipo=tipo), "retirada" if tipo == "saida" else tipo,
                    "data_movimento", "entrada__depositante", "cargas", ("documento", "destino"),
                    Case(When(estorno__isnull=False, then=Value("Estornado")), default=Value("Ativo")))
        incluir(EntregaVendaGraos.objects.all(), "entrega", "data_entrega", "venda__cliente_nome", "vendas",
                ("referencia_externa", "venda__numero_contrato"),
                Case(When(cancelado_em__isnull=False, then=Value("Cancelado")), default=Value("Ativo")), referencia=F("venda_id"))
        for entidade, (modulo, _) in ALVOS.items():
            incluir(AnexoLancamento.objects.filter(entidade=entidade, excluido_em__isnull=True), "anexo", "criado_em", "nome", modulo,
                    ("registro_id",), Value(entidade), F("registro_id"), download=False)
        if not fontes:
            return Response({"resultados": [], "total": 0, "pagina": filtros["pagina"], "total_paginas": 0})
        consulta = fontes[0].union(*fontes[1:], all=True).order_by("-doc_data", "doc_tipo", "-doc_numero")
        total = consulta.count()
        inicio = (filtros["pagina"] - 1) * 25
        return Response({"resultados": list(consulta[inicio:inicio + 25]), "total": total,
                         "pagina": filtros["pagina"], "total_paginas": (total + 24) // 25})


class ConferenciaFinanceiraView(NoStoreResponseMixin, APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        if not pode(request.user, "financeiro", "consultar"):
            raise PermissionDenied()
        entrada = FiltrosGestao(data=request.query_params)
        entrada.is_valid(raise_exception=True)
        f = entrada.validated_data
        decimal = DecimalField(max_digits=14, decimal_places=2)
        qs = LancamentoFinanceiro.objects.all().annotate(
            diferenca=F("valor") - Coalesce("valor_liquidado", Value(0), output_field=decimal),
        )
        if f["somente_diferencas"]:
            qs = qs.filter(status="liquidado").exclude(diferenca=0)
        if f["busca"]:
            qs = qs.filter(Q(descricao__icontains=f["busca"]) | Q(parceiro__nome__icontains=f["busca"]))
        if f.get("inicio"):
            qs = qs.filter(data_liquidacao__gte=f["inicio"])
        if f.get("fim"):
            qs = qs.filter(data_liquidacao__lte=f["fim"])
        total = qs.count()
        # Separar faltas e excedentes evita que divergências opostas se anulem.
        resumo = {"a_menor": qs.filter(status="liquidado", diferenca__gt=0).aggregate(v=Sum("diferenca"))["v"] or 0,
                  "a_maior": -(qs.filter(status="liquidado", diferenca__lt=0).aggregate(v=Sum("diferenca"))["v"] or 0)}
        inicio = (f["pagina"] - 1) * 25
        itens = qs.order_by("-data_liquidacao", "-id").values("id", "tipo", "status", "descricao", "valor", "valor_liquidado", "diferenca", "data_liquidacao")[inicio:inicio + 25]
        return Response({"resultados": list(itens), "total": total, "pagina": f["pagina"], "total_paginas": (total + 24) // 25, "resumo": resumo})

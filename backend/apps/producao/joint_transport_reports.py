import csv
import io
from decimal import Decimal

from django.db.models import Avg, Count, Sum
from django.http import HttpResponse
from openpyxl import Workbook
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from .grain_reports import export_pdf
from .joint_models import CargaLoteConjunto
from .joint_services import lotes_conjuntos_visiveis


AGRUPAMENTOS = {"motorista", "placa", "periodo", "lote", "destino", "transportadora"}


def _queryset(request):
    lotes = lotes_conjuntos_visiveis(request.user).values_list("id", flat=True)
    queryset = CargaLoteConjunto.objects.filter(lote_id__in=lotes).select_related(
        "lote__cultura",
        "lote__safra",
        "motorista",
        "veiculo_cavalo",
        "transportadora",
    )
    filtros = {
        "lote_id": request.query_params.get("lote", "").strip(),
        "motorista_id": request.query_params.get("motorista", "").strip(),
        "veiculo_cavalo_id": request.query_params.get("veiculo", "").strip(),
        "transportadora_id": request.query_params.get("transportadora", "").strip(),
        "destino__icontains": request.query_params.get("destino", "").strip(),
        "lote__cultura_id": request.query_params.get("cultura", "").strip(),
        "lote__safra_id": request.query_params.get("safra", "").strip(),
        "lote__participantes__propriedade_id": request.query_params.get("propriedade", "").strip(),
    }
    for campo, valor in filtros.items():
        if valor:
            queryset = queryset.filter(**{campo: valor})
    inicio = request.query_params.get("data_inicio", "").strip()
    fim = request.query_params.get("data_fim", "").strip()
    if inicio:
        queryset = queryset.filter(data_hora__date__gte=inicio)
    if fim:
        queryset = queryset.filter(data_hora__date__lte=fim)
    return queryset.distinct()


def _linhas(queryset, agrupamento):
    if agrupamento == "motorista":
        valores = ("motorista_id", "motorista__nome")
        rotulo = lambda item: item["motorista__nome"] or "Não informado"
    elif agrupamento == "placa":
        valores = ("veiculo_cavalo_id", "veiculo_cavalo__placa", "placa_cavalo_informada")
        rotulo = lambda item: item["veiculo_cavalo__placa"] or item["placa_cavalo_informada"] or "Não informada"
    elif agrupamento == "periodo":
        queryset = queryset.annotate(data_referencia=models.functions.TruncDate("data_hora"))
        valores = ("data_referencia",)
        rotulo = lambda item: str(item["data_referencia"])
    elif agrupamento == "destino":
        valores = ("destino",)
        rotulo = lambda item: item["destino"] or "Não informado"
    elif agrupamento == "transportadora":
        valores = ("transportadora_id", "transportadora__nome")
        rotulo = lambda item: item["transportadora__nome"] or "Não informada"
    else:
        valores = ("lote_id", "lote__codigo")
        rotulo = lambda item: item["lote__codigo"]
    agregados = (
        queryset.values(*valores)
        .annotate(
            viagens=Count("id"),
            quantidade_kg=Sum("peso_liquido_kg"),
            peso_medio_kg=Avg("peso_liquido_kg"),
        )
        .order_by(*valores)
    )
    return [
        {
            "agrupamento": agrupamento,
            "referencia": rotulo(item),
            "viagens": item["viagens"],
            "quantidade_kg": item["quantidade_kg"] or Decimal("0"),
            "peso_medio_kg": item["peso_medio_kg"] or Decimal("0"),
        }
        for item in agregados
    ]


def _csv(linhas):
    output = io.StringIO()
    campos = ["agrupamento", "referencia", "viagens", "quantidade_kg", "peso_medio_kg"]
    writer = csv.DictWriter(output, fieldnames=campos)
    writer.writeheader()
    writer.writerows(linhas)
    response = HttpResponse(output.getvalue(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="transportes-lotes-conjuntos.csv"'
    return response


def _xlsx(linhas):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Transportes conjuntos"
    campos = ["agrupamento", "referencia", "viagens", "quantidade_kg", "peso_medio_kg"]
    sheet.append(campos)
    for linha in linhas:
        sheet.append([str(linha[campo]) for campo in campos])
    output = io.BytesIO()
    workbook.save(output)
    response = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="transportes-lotes-conjuntos.xlsx"'
    return response


def _pdf(linhas):
    adaptadas = [
        {
            "data": linha["agrupamento"],
            "propriedade": linha["referencia"],
            "cadpro": f"{linha['viagens']} viagem(ns)",
            "cultura": "Transporte conjunto",
            "safra": "—",
            "peso_liquido_kg": linha["quantidade_kg"],
            "sacas": f"média {linha['peso_medio_kg']} kg",
        }
        for linha in linhas
    ]
    response = HttpResponse(export_pdf(adaptadas), content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="transportes-lotes-conjuntos.pdf"'
    return response


class RelatorioTransporteLoteConjuntoView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        agrupamento = request.query_params.get("agrupamento", "motorista").strip().lower()
        if agrupamento not in AGRUPAMENTOS:
            agrupamento = "motorista"
        linhas = _linhas(_queryset(request), agrupamento)
        formato = request.query_params.get("formato", "csv").strip().lower()
        if formato == "xlsx":
            return _xlsx(linhas)
        if formato == "pdf":
            return _pdf(linhas)
        return _csv(linhas)

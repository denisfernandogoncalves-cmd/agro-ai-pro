import csv
import io
from decimal import Decimal

from django.db.models import Avg, Count, Sum
from openpyxl import Workbook

from .grain_access import filtrar_queryset_por_cadpro
from .grain_models import (
    ContratoProducao,
    EmbarqueProducao,
    RecebimentoProducao,
    SaldoGraos,
)


REPORT_COLUMNS = (
    ("data", "Data"),
    ("propriedade", "Propriedade"),
    ("cadpro", "CAD/PRO"),
    ("talhao", "Talhão"),
    ("cultura", "Cultura"),
    ("safra", "Safra"),
    ("local", "Local de armazenagem"),
    ("peso_liquido_kg", "Peso líquido (kg)"),
    ("sacas", "Sacas"),
    ("umidade", "Umidade (%)"),
    ("impureza", "Impureza (%)"),
    ("defeitos", "Defeitos (%)"),
    ("romaneio", "Romaneio"),
)


def _apply_filters(queryset, params):
    filters = {}
    for param, field in (
        ("propriedade", "propriedade_id"),
        ("cadpro", "cadpro_id"),
        ("talhao", "talhao_id"),
        ("cultura", "cultura_id"),
        ("safra", "safra_id"),
        ("local", "local_armazenagem_id"),
    ):
        value = str(params.get(param, "")).strip()
        if value:
            filters[field] = value
    start = str(params.get("data_inicio", "")).strip()
    end = str(params.get("data_fim", "")).strip()
    if start:
        filters["data__date__gte"] = start
    if end:
        filters["data__date__lte"] = end
    return queryset.filter(**filters)


def production_queryset(user, params):
    queryset = RecebimentoProducao.objects.select_related(
        "propriedade",
        "cadpro",
        "talhao",
        "cultura",
        "safra",
        "local_armazenagem",
    ).filter(status=RecebimentoProducao.Status.CONFIRMADO)
    queryset = filtrar_queryset_por_cadpro(queryset, user)
    return _apply_filters(queryset, params)


def dashboard_data(user, params):
    receipts = production_queryset(user, params)
    balances = filtrar_queryset_por_cadpro(
        SaldoGraos.objects.select_related("propriedade", "cadpro", "cultura", "safra"),
        user,
    )
    shipments = filtrar_queryset_por_cadpro(
        EmbarqueProducao.objects.filter(status=EmbarqueProducao.Status.CONFIRMADO),
        user,
    )
    contracts = filtrar_queryset_por_cadpro(
        ContratoProducao.objects.filter(status=ContratoProducao.Status.ABERTO),
        user,
    )
    for params_name, field in (("propriedade", "propriedade_id"), ("cadpro", "cadpro_id"), ("cultura", "cultura_id"), ("safra", "safra_id")):
        value = str(params.get(params_name, "")).strip()
        if value:
            balances = balances.filter(**{field: value})
            shipments = shipments.filter(**{field: value})
            contracts = contracts.filter(**{field: value})

    totals = receipts.aggregate(
        producao_kg=Sum("peso_liquido_kg"),
        sacas=Sum("quantidade_sacas"),
        cargas=Count("id"),
        umidade_media=Avg("umidade_percentual"),
        impureza_media=Avg("impureza_percentual"),
        defeitos_media=Avg("defeitos_percentual"),
    )
    shipment_totals = shipments.aggregate(
        quantidade_kg=Sum("quantidade_kg"),
        valor=Sum("valor_total"),
        embarques=Count("id"),
    )
    stock_kg = balances.aggregate(total=Sum("quantidade_kg"))["total"] or Decimal("0")
    return {
        "producao": {
            "peso_liquido_kg": totals["producao_kg"] or Decimal("0"),
            "sacas": totals["sacas"] or Decimal("0"),
            "cargas": totals["cargas"],
        },
        "qualidade": {
            "umidade_media": totals["umidade_media"],
            "impureza_media": totals["impureza_media"],
            "defeitos_media": totals["defeitos_media"],
        },
        "estoque": {"disponivel_kg": stock_kg, "posicoes": balances.count()},
        "embarques": {
            "quantidade_kg": shipment_totals["quantidade_kg"] or Decimal("0"),
            "valor_total": shipment_totals["valor"] or Decimal("0"),
            "total": shipment_totals["embarques"],
        },
        "contratos": {"abertos": contracts.count()},
        "por_propriedade": list(
            receipts.values("propriedade_id", "propriedade__nome")
            .annotate(peso_kg=Sum("peso_liquido_kg"), sacas=Sum("quantidade_sacas"))
            .order_by("propriedade__nome")
        ),
        "por_cadpro": list(
            receipts.values("cadpro_id", "cadpro__codigo")
            .annotate(peso_kg=Sum("peso_liquido_kg"), sacas=Sum("quantidade_sacas"))
            .order_by("cadpro__codigo")
        ),
        "por_talhao": list(
            receipts.exclude(talhao=None)
            .values("talhao_id", "talhao__nome")
            .annotate(peso_kg=Sum("peso_liquido_kg"), sacas=Sum("quantidade_sacas"))
            .order_by("talhao__nome")
        ),
    }


def report_rows(queryset):
    for item in queryset:
        yield {
            "data": item.data.date().isoformat(),
            "propriedade": item.propriedade.nome,
            "cadpro": item.cadpro.codigo,
            "talhao": item.talhao.nome if item.talhao_id else "",
            "cultura": item.cultura.nome,
            "safra": item.safra.nome,
            "local": item.local_armazenagem.nome,
            "peso_liquido_kg": item.peso_liquido_kg,
            "sacas": item.quantidade_sacas,
            "umidade": item.umidade_percentual,
            "impureza": item.impureza_percentual,
            "defeitos": item.defeitos_percentual,
            "romaneio": item.romaneio,
        }


def export_csv(rows):
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow([label for _, label in REPORT_COLUMNS])
    for row in rows:
        writer.writerow([row[key] for key, _ in REPORT_COLUMNS])
    return output.getvalue().encode("utf-8-sig")


def export_xlsx(rows):
    workbook = Workbook(write_only=True)
    sheet = workbook.create_sheet("Produção")
    sheet.append([label for _, label in REPORT_COLUMNS])
    for row in rows:
        sheet.append([row[key] for key, _ in REPORT_COLUMNS])
    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


def _pdf_escape(value):
    text = str(value).encode("latin-1", "replace").decode("latin-1")
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def export_pdf(rows):
    lines = ["AGRO-AI-PRO - Relatório de Produção"]
    for row in rows:
        lines.append(
            f"{row['data']} | {row['propriedade']} | {row['cadpro']} | {row['cultura']} | "
            f"{row['safra']} | {row['peso_liquido_kg']} kg | {row['sacas']} sc"
        )
    pages = [lines[index:index + 45] for index in range(0, len(lines), 45)] or [[]]
    objects = []
    page_ids = []
    font_id = 3
    next_id = 4
    content_entries = []
    for page_lines in pages:
        content = ["BT", "/F1 9 Tf", "40 800 Td", "12 TL"]
        for line in page_lines:
            content.append(f"({_pdf_escape(line)}) Tj")
            content.append("T*")
        content.append("ET")
        stream = "\n".join(content).encode("latin-1")
        content_id = next_id
        page_id = next_id + 1
        next_id += 2
        content_entries.append((content_id, stream))
        page_ids.append(page_id)
    objects.append((1, f"<< /Type /Catalog /Pages 2 0 R >>".encode()))
    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects.append((2, f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode()))
    objects.append((font_id, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"))
    for (content_id, stream), page_id in zip(content_entries, page_ids):
        objects.append((content_id, b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream"))
        objects.append((page_id, f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>".encode()))
    objects.sort(key=lambda item: item[0])
    output = io.BytesIO()
    output.write(b"%PDF-1.4\n")
    offsets = {0: 0}
    for object_id, body in objects:
        offsets[object_id] = output.tell()
        output.write(f"{object_id} 0 obj\n".encode())
        output.write(body)
        output.write(b"\nendobj\n")
    xref = output.tell()
    max_id = max(offsets)
    output.write(f"xref\n0 {max_id + 1}\n".encode())
    output.write(b"0000000000 65535 f \n")
    for object_id in range(1, max_id + 1):
        output.write(f"{offsets.get(object_id, 0):010d} 00000 n \n".encode())
    output.write(f"trailer\n<< /Size {max_id + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode())
    return output.getvalue()

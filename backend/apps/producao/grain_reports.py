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
    ("tipo", "Tipo"),
    ("data", "Data"),
    ("propriedade", "Propriedade"),
    ("cadpro", "CAD/PRO"),
    ("talhao", "Talhão"),
    ("cultura", "Cultura"),
    ("safra", "Safra"),
    ("local", "Local de armazenagem"),
    ("comprador", "Comprador"),
    ("contrato", "Contrato"),
    ("motorista", "Motorista"),
    ("placa", "Placa"),
    ("romaneio", "Romaneio"),
    ("quantidade_kg", "Quantidade (kg)"),
    ("sacas", "Sacas"),
    ("preco_saca", "Preço por saca"),
    ("valor", "Valor"),
    ("umidade", "Umidade (%)"),
    ("impureza", "Impureza (%)"),
    ("defeitos", "Defeitos (%)"),
    ("status", "Status"),
)


def _value(params, name):
    return str(params.get(name, "")).strip()


def _apply_common_filters(queryset, params, *, date_field=None):
    for parameter, field in (
        ("propriedade", "propriedade_id"),
        ("cadpro", "cadpro_id"),
        ("cultura", "cultura_id"),
        ("safra", "safra_id"),
    ):
        value = _value(params, parameter)
        if value:
            queryset = queryset.filter(**{field: value})
    if date_field:
        start = _value(params, "data_inicio")
        end = _value(params, "data_fim")
        if start:
            queryset = queryset.filter(**{f"{date_field}__gte": start})
        if end:
            queryset = queryset.filter(**{f"{date_field}__lte": end})
    return queryset


def _receipts_queryset(user, params):
    queryset = RecebimentoProducao.objects.select_related(
        "propriedade",
        "cadpro",
        "talhao",
        "cultura",
        "safra",
        "local_armazenagem",
        "motorista",
        "veiculo",
    ).filter(status=RecebimentoProducao.Status.CONFIRMADO)
    queryset = filtrar_queryset_por_cadpro(queryset, user)
    queryset = _apply_common_filters(queryset, params, date_field="data__date")
    for parameter, field in (
        ("talhao", "talhao_id"),
        ("local", "local_armazenagem_id"),
        ("motorista", "motorista_id"),
    ):
        value = _value(params, parameter)
        if value:
            queryset = queryset.filter(**{field: value})
    placa = _value(params, "placa")
    if placa:
        queryset = queryset.filter(veiculo__placa__icontains=placa) | queryset.filter(
            placa_informada__icontains=placa
        )
    return queryset.distinct()


def _shipments_queryset(user, params):
    queryset = EmbarqueProducao.objects.select_related(
        "propriedade",
        "cadpro",
        "cultura",
        "safra",
        "local_armazenagem",
        "comprador",
        "contrato",
        "motorista",
        "veiculo",
    )
    queryset = filtrar_queryset_por_cadpro(queryset, user)
    queryset = _apply_common_filters(queryset, params, date_field="data__date")
    for parameter, field in (
        ("local", "local_armazenagem_id"),
        ("comprador", "comprador_id"),
        ("contrato", "contrato_id"),
        ("motorista", "motorista_id"),
        ("status", "status"),
    ):
        value = _value(params, parameter)
        if value:
            queryset = queryset.filter(**{field: value})
    placa = _value(params, "placa")
    if placa:
        queryset = queryset.filter(veiculo__placa__icontains=placa) | queryset.filter(
            placa_informada__icontains=placa
        )
    return queryset.distinct()


def _balances_queryset(user, params):
    queryset = SaldoGraos.objects.select_related(
        "propriedade",
        "cadpro",
        "talhao",
        "cultura",
        "safra",
        "local_armazenagem",
    )
    queryset = filtrar_queryset_por_cadpro(queryset, user)
    queryset = _apply_common_filters(queryset, params)
    for parameter, field in (
        ("talhao", "talhao_id"),
        ("local", "local_armazenagem_id"),
    ):
        value = _value(params, parameter)
        if value:
            queryset = queryset.filter(**{field: value})
    return queryset


def _contracts_queryset(user, params):
    queryset = ContratoProducao.objects.select_related(
        "propriedade",
        "cadpro",
        "cultura",
        "safra",
        "comprador",
    ).prefetch_related("embarques")
    queryset = filtrar_queryset_por_cadpro(queryset, user)
    queryset = _apply_common_filters(queryset, params, date_field="data_contrato")
    for parameter, field in (
        ("comprador", "comprador_id"),
        ("status", "status"),
    ):
        value = _value(params, parameter)
        if value:
            queryset = queryset.filter(**{field: value})
    contract = _value(params, "contrato")
    if contract:
        queryset = queryset.filter(id=contract)
    return queryset


def production_queryset(user, params):
    report_type = _value(params, "tipo") or "recebimentos"
    factories = {
        "recebimentos": _receipts_queryset,
        "embarques": _shipments_queryset,
        "estoque": _balances_queryset,
        "contratos": _contracts_queryset,
    }
    if report_type not in factories:
        raise ValueError("Tipo inválido. Use recebimentos, embarques, estoque ou contratos.")
    return factories[report_type](user, params)


def dashboard_data(user, params):
    receipts = _receipts_queryset(user, params)
    balances = _balances_queryset(user, params)
    shipments = _shipments_queryset(user, params).filter(
        status=EmbarqueProducao.Status.CONFIRMADO
    )
    contracts = _contracts_queryset(user, params).filter(
        status=ContratoProducao.Status.ABERTO
    )

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

    by_field = []
    for item in (
        receipts.exclude(talhao=None)
        .values("talhao_id", "talhao__nome", "talhao__area_hectares")
        .annotate(peso_kg=Sum("peso_liquido_kg"), sacas=Sum("quantidade_sacas"))
        .order_by("talhao__nome")
    ):
        area = Decimal(str(item["talhao__area_hectares"] or 0))
        item["produtividade_sacas_ha"] = (
            item["sacas"] / area if area > 0 and item["sacas"] is not None else None
        )
        by_field.append(item)

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
        "por_talhao": by_field,
    }


def _empty_row(report_type):
    return {key: "" for key, _ in REPORT_COLUMNS} | {"tipo": report_type}


def report_rows(queryset):
    for item in queryset:
        if isinstance(item, RecebimentoProducao):
            row = _empty_row("Recebimento")
            row.update(
                data=item.data.date().isoformat(),
                propriedade=item.propriedade.nome,
                cadpro=item.cadpro.codigo,
                talhao=item.talhao.nome if item.talhao_id else "",
                cultura=item.cultura.nome,
                safra=item.safra.nome,
                local=item.local_armazenagem.nome,
                motorista=item.motorista.nome if item.motorista_id else "",
                placa=item.veiculo.placa if item.veiculo_id else item.placa_informada,
                romaneio=item.romaneio,
                quantidade_kg=item.peso_liquido_kg,
                sacas=item.quantidade_sacas,
                umidade=item.umidade_percentual,
                impureza=item.impureza_percentual,
                defeitos=item.defeitos_percentual,
                status=item.status,
            )
        elif isinstance(item, EmbarqueProducao):
            row = _empty_row("Embarque")
            row.update(
                data=item.data.date().isoformat(),
                propriedade=item.propriedade.nome,
                cadpro=item.cadpro.codigo,
                cultura=item.cultura.nome,
                safra=item.safra.nome,
                local=item.local_armazenagem.nome,
                comprador=item.comprador.nome,
                contrato=item.contrato.numero if item.contrato_id else "",
                motorista=item.motorista.nome if item.motorista_id else "",
                placa=item.veiculo.placa if item.veiculo_id else item.placa_informada,
                romaneio=item.romaneio,
                quantidade_kg=item.quantidade_kg,
                sacas=item.quantidade_sacas,
                preco_saca=item.preco_saca,
                valor=item.valor_total,
                status=item.status,
            )
        elif isinstance(item, SaldoGraos):
            row = _empty_row("Estoque")
            row.update(
                propriedade=item.propriedade.nome,
                cadpro=item.cadpro.codigo,
                talhao=item.talhao.nome if item.talhao_id else "",
                cultura=item.cultura.nome,
                safra=item.safra.nome,
                local=item.local_armazenagem.nome,
                quantidade_kg=item.quantidade_kg,
                sacas=item.quantidade_sacas,
                status="disponível",
            )
        else:
            row = _empty_row("Contrato")
            shipped = sum(
                (
                    shipment.quantidade_kg
                    for shipment in item.embarques.all()
                    if shipment.status == EmbarqueProducao.Status.CONFIRMADO
                ),
                start=Decimal("0"),
            )
            row.update(
                data=item.data_contrato.isoformat(),
                propriedade=item.propriedade.nome,
                cadpro=item.cadpro.codigo,
                cultura=item.cultura.nome,
                safra=item.safra.nome,
                comprador=item.comprador.nome,
                contrato=item.numero,
                quantidade_kg=item.quantidade_kg,
                sacas=item.quantidade_kg / item.cultura.peso_saca_kg,
                preco_saca=item.preco_saca,
                valor=(item.quantidade_kg / item.cultura.peso_saca_kg) * item.preco_saca,
                status=f"{item.status}; embarcado {shipped} kg",
            )
        yield row


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
    lines = ["AGRO-AI-PRO - Relatório Integrado de Produção"]
    for row in rows:
        lines.append(
            f"{row['tipo']} | {row['data']} | {row['propriedade']} | {row['cadpro']} | "
            f"{row['cultura']} | {row['safra']} | {row['quantidade_kg']} kg | {row['status']}"
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
    objects.append((1, b"<< /Type /Catalog /Pages 2 0 R >>"))
    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects.append((2, f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode()))
    objects.append((font_id, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"))
    for (content_id, stream), page_id in zip(content_entries, page_ids):
        objects.append((content_id, b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream"))
        objects.append((page_id, f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>".encode()))
    objects.sort(key=lambda value: value[0])
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

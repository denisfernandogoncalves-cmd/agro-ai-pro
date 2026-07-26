import csv
import io
from decimal import Decimal

from django.db.models import Avg, Count, Sum
from openpyxl import Workbook

from .grain_access import filtrar_queryset_por_cadpro
from .grain_enterprise_models import ConfiguracaoCultura, DetalheLocalArmazenagem
from .grain_models import (
    ContratoProducao,
    EmbarqueProducao,
    RecebimentoProducao,
    SaldoGraos,
)


REPORT_DEFINITIONS = {
    "recebimentos": (
        ("data", "Data"),
        ("propriedade", "Propriedade"),
        ("cadpro", "CAD/PRO"),
        ("talhao", "Talhão"),
        ("cultura", "Cultura"),
        ("safra", "Safra"),
        ("motorista", "Motorista"),
        ("placa", "Placa"),
        ("local", "Local de armazenagem"),
        ("peso_bruto_kg", "Peso bruto (kg)"),
        ("peso_liquido_kg", "Peso líquido (kg)"),
        ("sacas", "Sacas"),
        ("umidade", "Umidade (%)"),
        ("impureza", "Impureza (%)"),
        ("defeitos", "Defeitos (%)"),
        ("romaneio", "Romaneio"),
    ),
    "embarques": (
        ("data", "Data"),
        ("propriedade", "Propriedade"),
        ("cadpro", "CAD/PRO"),
        ("cultura", "Cultura"),
        ("safra", "Safra"),
        ("comprador", "Comprador"),
        ("contrato", "Contrato"),
        ("motorista", "Motorista"),
        ("placa", "Placa"),
        ("destino", "Destino"),
        ("local", "Local de armazenagem"),
        ("romaneio", "Romaneio"),
        ("nota_produtor", "Nota do produtor"),
        ("nota_empresa", "Nota da empresa"),
        ("quantidade_kg", "Quantidade (kg)"),
        ("sacas", "Sacas"),
        ("preco_saca", "Preço por saca"),
        ("valor_total", "Valor total"),
    ),
    "contratos": (
        ("data", "Data do contrato"),
        ("propriedade", "Propriedade"),
        ("cadpro", "CAD/PRO"),
        ("cultura", "Cultura"),
        ("safra", "Safra"),
        ("comprador", "Comprador"),
        ("contrato", "Contrato"),
        ("data_limite", "Data limite"),
        ("quantidade_kg", "Quantidade contratada (kg)"),
        ("embarcado_kg", "Quantidade embarcada (kg)"),
        ("saldo_kg", "Saldo do contrato (kg)"),
        ("preco_saca", "Preço por saca"),
        ("status", "Status"),
    ),
    "estoque": (
        ("propriedade", "Propriedade"),
        ("cadpro", "CAD/PRO"),
        ("talhao", "Talhão"),
        ("cultura", "Cultura"),
        ("safra", "Safra"),
        ("local", "Local de armazenagem"),
        ("quantidade_kg", "Quantidade (kg)"),
        ("sacas", "Sacas"),
        ("atualizado_em", "Atualizado em"),
    ),
}


def _filter_value(params, key):
    return str(params.get(key, "")).strip()


def _apply_dimensions(queryset, params, mapping):
    filters = {}
    for parameter, field in mapping:
        value = _filter_value(params, parameter)
        if value:
            filters[field] = value
    return queryset.filter(**filters)


def _apply_period(queryset, params, field="data"):
    start = _filter_value(params, "data_inicio")
    end = _filter_value(params, "data_fim")
    if start:
        queryset = queryset.filter(**{f"{field}__date__gte": start})
    if end:
        queryset = queryset.filter(**{f"{field}__date__lte": end})
    return queryset


def receipts_queryset(user, params):
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
    queryset = _apply_dimensions(
        queryset,
        params,
        (
            ("propriedade", "propriedade_id"),
            ("cadpro", "cadpro_id"),
            ("talhao", "talhao_id"),
            ("cultura", "cultura_id"),
            ("safra", "safra_id"),
            ("local", "local_armazenagem_id"),
            ("motorista", "motorista_id"),
            ("placa", "placa_informada__iexact"),
        ),
    )
    return _apply_period(queryset, params)


def shipments_queryset(user, params):
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
    ).filter(status=EmbarqueProducao.Status.CONFIRMADO)
    queryset = filtrar_queryset_por_cadpro(queryset, user)
    queryset = _apply_dimensions(
        queryset,
        params,
        (
            ("propriedade", "propriedade_id"),
            ("cadpro", "cadpro_id"),
            ("cultura", "cultura_id"),
            ("safra", "safra_id"),
            ("local", "local_armazenagem_id"),
            ("comprador", "comprador_id"),
            ("contrato", "contrato_id"),
            ("motorista", "motorista_id"),
            ("placa", "placa_informada__iexact"),
        ),
    )
    return _apply_period(queryset, params)


def contracts_queryset(user, params):
    queryset = ContratoProducao.objects.select_related(
        "propriedade",
        "cadpro",
        "cultura",
        "safra",
        "comprador",
    ).prefetch_related("embarques")
    queryset = filtrar_queryset_por_cadpro(queryset, user)
    return _apply_dimensions(
        queryset,
        params,
        (
            ("propriedade", "propriedade_id"),
            ("cadpro", "cadpro_id"),
            ("cultura", "cultura_id"),
            ("safra", "safra_id"),
            ("comprador", "comprador_id"),
            ("contrato", "id"),
            ("status", "status"),
        ),
    )


def balances_queryset(user, params):
    queryset = SaldoGraos.objects.select_related(
        "propriedade",
        "cadpro",
        "talhao",
        "cultura",
        "safra",
        "local_armazenagem",
    )
    queryset = filtrar_queryset_por_cadpro(queryset, user)
    return _apply_dimensions(
        queryset,
        params,
        (
            ("propriedade", "propriedade_id"),
            ("cadpro", "cadpro_id"),
            ("talhao", "talhao_id"),
            ("cultura", "cultura_id"),
            ("safra", "safra_id"),
            ("local", "local_armazenagem_id"),
        ),
    )


def _productivity(receipts):
    rows = []
    for item in (
        receipts.exclude(talhao=None)
        .values("talhao_id", "talhao__nome", "talhao__area_hectares")
        .annotate(sacas=Sum("quantidade_sacas"), peso_kg=Sum("peso_liquido_kg"))
    ):
        area = Decimal(str(item["talhao__area_hectares"] or 0))
        if area <= 0:
            continue
        rows.append(
            {
                "talhao_id": item["talhao_id"],
                "talhao_nome": item["talhao__nome"],
                "area_hectares": area,
                "peso_kg": item["peso_kg"] or Decimal("0"),
                "sacas": item["sacas"] or Decimal("0"),
                "sacas_hectare": (item["sacas"] or Decimal("0")) / area,
            }
        )
    rows.sort(key=lambda row: row["sacas_hectare"], reverse=True)
    return rows


def dashboard_data_enterprise(user, params):
    receipts = receipts_queryset(user, params)
    balances = balances_queryset(user, params)
    shipments = shipments_queryset(user, params)
    contracts = contracts_queryset(user, params)

    production = receipts.aggregate(
        peso_liquido_kg=Sum("peso_liquido_kg"),
        sacas=Sum("quantidade_sacas"),
        cargas=Count("id"),
        umidade_media=Avg("umidade_percentual"),
        impureza_media=Avg("impureza_percentual"),
        defeitos_media=Avg("defeitos_percentual"),
    )
    shipment_totals = shipments.aggregate(
        quantidade_kg=Sum("quantidade_kg"),
        valor_total=Sum("valor_total"),
        total=Count("id"),
    )
    stock_total = balances.aggregate(total=Sum("quantidade_kg"))["total"] or Decimal("0")
    productivity = _productivity(receipts)

    culture_config = {
        config.cultura_id: config
        for config in ConfiguracaoCultura.objects.select_related("cultura")
    }
    quality_alerts = []
    for item in receipts.order_by("-umidade_percentual")[:100]:
        config = culture_config.get(item.cultura_id)
        limit = config.umidade_alerta_percentual if config else Decimal("14")
        if item.umidade_percentual > limit:
            quality_alerts.append(
                {
                    "recebimento_id": item.id,
                    "cultura": item.cultura.nome,
                    "umidade_percentual": item.umidade_percentual,
                    "limite_percentual": limit,
                }
            )

    stock_alerts = []
    stock_by_culture = balances.values("cultura_id", "cultura__nome").annotate(
        quantidade_kg=Sum("quantidade_kg")
    )
    for item in stock_by_culture:
        config = culture_config.get(item["cultura_id"])
        minimum = config.estoque_minimo_kg if config else Decimal("0")
        if minimum > 0 and (item["quantidade_kg"] or Decimal("0")) < minimum:
            stock_alerts.append(
                {
                    "cultura_id": item["cultura_id"],
                    "cultura": item["cultura__nome"],
                    "quantidade_kg": item["quantidade_kg"] or Decimal("0"),
                    "minimo_kg": minimum,
                }
            )

    contract_alerts = []
    open_contracts = contracts.filter(status=ContratoProducao.Status.ABERTO)
    for contract in open_contracts:
        shipped = sum(
            (
                shipment.quantidade_kg
                for shipment in contract.embarques.all()
                if shipment.status == EmbarqueProducao.Status.CONFIRMADO
            ),
            start=Decimal("0"),
        )
        remaining = max(contract.quantidade_kg - shipped, Decimal("0"))
        percent = remaining / contract.quantidade_kg * Decimal("100") if contract.quantidade_kg else Decimal("0")
        if percent <= Decimal("10"):
            contract_alerts.append(
                {
                    "contrato_id": contract.id,
                    "numero": contract.numero,
                    "saldo_kg": remaining,
                    "percentual_restante": percent,
                }
            )

    storage_capacity = DetalheLocalArmazenagem.objects.filter(
        local_id__in=balances.values_list("local_armazenagem_id", flat=True),
        ativo=True,
    ).aggregate(total=Sum("capacidade_kg"))["total"]

    return {
        "producao": {
            "peso_liquido_kg": production["peso_liquido_kg"] or Decimal("0"),
            "sacas": production["sacas"] or Decimal("0"),
            "cargas": production["cargas"],
        },
        "produtividade": {
            "media_sacas_hectare": (
                sum((row["sacas"] for row in productivity), start=Decimal("0"))
                / sum((row["area_hectares"] for row in productivity), start=Decimal("0"))
                if productivity
                else None
            ),
            "melhor_talhao": productivity[0] if productivity else None,
            "menor_talhao": productivity[-1] if productivity else None,
            "por_talhao": productivity,
        },
        "qualidade": {
            "umidade_media": production["umidade_media"],
            "impureza_media": production["impureza_media"],
            "defeitos_media": production["defeitos_media"],
            "alertas": quality_alerts,
        },
        "estoque": {
            "disponivel_kg": stock_total,
            "posicoes": balances.count(),
            "alertas_minimo": stock_alerts,
            "capacidade_mapeada_kg": storage_capacity,
        },
        "embarques": {
            "quantidade_kg": shipment_totals["quantidade_kg"] or Decimal("0"),
            "valor_total": shipment_totals["valor_total"] or Decimal("0"),
            "total": shipment_totals["total"],
        },
        "contratos": {
            "abertos": open_contracts.count(),
            "alertas_limite": contract_alerts,
        },
        "saldo_disponivel_kg": stock_total,
        "receita": shipment_totals["valor_total"] or Decimal("0"),
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
    }


def report_data(user, params):
    report_type = _filter_value(params, "tipo") or "recebimentos"
    if report_type not in REPORT_DEFINITIONS:
        raise ValueError("Tipo de relatório inválido. Use recebimentos, embarques, contratos ou estoque.")
    if report_type == "recebimentos":
        queryset = receipts_queryset(user, params)
        rows = [
            {
                "data": item.data.date().isoformat(),
                "propriedade": item.propriedade.nome,
                "cadpro": item.cadpro.codigo,
                "talhao": item.talhao.nome if item.talhao_id else "",
                "cultura": item.cultura.nome,
                "safra": item.safra.nome,
                "motorista": item.motorista.nome if item.motorista_id else "",
                "placa": item.veiculo.placa if item.veiculo_id else item.placa_informada,
                "local": item.local_armazenagem.nome,
                "peso_bruto_kg": item.peso_bruto_kg,
                "peso_liquido_kg": item.peso_liquido_kg,
                "sacas": item.quantidade_sacas,
                "umidade": item.umidade_percentual,
                "impureza": item.impureza_percentual,
                "defeitos": item.defeitos_percentual,
                "romaneio": item.romaneio,
            }
            for item in queryset
        ]
    elif report_type == "embarques":
        queryset = shipments_queryset(user, params)
        rows = [
            {
                "data": item.data.date().isoformat(),
                "propriedade": item.propriedade.nome,
                "cadpro": item.cadpro.codigo,
                "cultura": item.cultura.nome,
                "safra": item.safra.nome,
                "comprador": item.comprador.nome,
                "contrato": item.contrato.numero if item.contrato_id else "",
                "motorista": item.motorista.nome if item.motorista_id else "",
                "placa": item.veiculo.placa if item.veiculo_id else item.placa_informada,
                "destino": item.destino,
                "local": item.local_armazenagem.nome,
                "romaneio": item.romaneio,
                "nota_produtor": item.nota_produtor,
                "nota_empresa": item.nota_empresa,
                "quantidade_kg": item.quantidade_kg,
                "sacas": item.quantidade_sacas,
                "preco_saca": item.preco_saca,
                "valor_total": item.valor_total,
            }
            for item in queryset
        ]
    elif report_type == "contratos":
        queryset = contracts_queryset(user, params)
        rows = []
        for item in queryset:
            shipped = sum(
                (
                    shipment.quantidade_kg
                    for shipment in item.embarques.all()
                    if shipment.status == EmbarqueProducao.Status.CONFIRMADO
                ),
                start=Decimal("0"),
            )
            rows.append(
                {
                    "data": item.data_contrato.isoformat(),
                    "propriedade": item.propriedade.nome,
                    "cadpro": item.cadpro.codigo,
                    "cultura": item.cultura.nome,
                    "safra": item.safra.nome,
                    "comprador": item.comprador.nome,
                    "contrato": item.numero,
                    "data_limite": item.data_limite.isoformat() if item.data_limite else "",
                    "quantidade_kg": item.quantidade_kg,
                    "embarcado_kg": shipped,
                    "saldo_kg": max(item.quantidade_kg - shipped, Decimal("0")),
                    "preco_saca": item.preco_saca,
                    "status": item.get_status_display(),
                }
            )
    else:
        queryset = balances_queryset(user, params)
        rows = [
            {
                "propriedade": item.propriedade.nome,
                "cadpro": item.cadpro.codigo,
                "talhao": item.talhao.nome if item.talhao_id else "",
                "cultura": item.cultura.nome,
                "safra": item.safra.nome,
                "local": item.local_armazenagem.nome,
                "quantidade_kg": item.quantidade_kg,
                "sacas": item.quantidade_sacas,
                "atualizado_em": item.atualizado_em.isoformat(),
            }
            for item in queryset
        ]
    return report_type, REPORT_DEFINITIONS[report_type], rows


def export_csv(columns, rows):
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow([label for _, label in columns])
    for row in rows:
        writer.writerow([row.get(key, "") for key, _ in columns])
    return output.getvalue().encode("utf-8-sig")


def export_xlsx(columns, rows):
    workbook = Workbook(write_only=True)
    sheet = workbook.create_sheet("Produção")
    sheet.append([label for _, label in columns])
    for row in rows:
        sheet.append([row.get(key, "") for key, _ in columns])
    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


def _pdf_escape(value):
    text = str(value).encode("latin-1", "replace").decode("latin-1")
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def export_pdf(columns, rows, title):
    lines = [f"AGRO-AI-PRO - {title}"]
    visible_columns = columns[:7]
    for row in rows:
        lines.append(" | ".join(str(row.get(key, "")) for key, _ in visible_columns))
    pages = [lines[index:index + 45] for index in range(0, len(lines), 45)] or [[]]
    objects = []
    page_ids = []
    font_id = 3
    next_id = 4
    content_entries = []
    for page_lines in pages:
        content = ["BT", "/F1 8 Tf", "30 810 Td", "11 TL"]
        for line in page_lines:
            content.extend((f"({_pdf_escape(line)}) Tj", "T*"))
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

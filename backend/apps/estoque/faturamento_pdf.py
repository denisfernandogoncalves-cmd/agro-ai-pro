"""PDF individual a partir do snapshot, sem consultar cadastros alterados depois do envio."""
from decimal import Decimal
from io import BytesIO
import re
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .faturamento import fornecedor_usa_bep


def numero(valor):
    texto = f"{Decimal(str(valor)):,.3f}".rstrip("0").rstrip(".")
    return texto.replace(",", "_").replace(".", ",").replace("_", ".")


def titulo_faturamento(resumo):
    def quantidade(valor):
        return numero(valor).replace(".", "")
    partes = [resumo["produto_nome"],
              f"{quantidade(resumo['total_embalagens'])} {resumo['embalagem']} DE {quantidade(resumo['conteudo_embalagem'])} {resumo['unidade']}",
              "SAFRA " + (resumo.get("safra", "").strip() or "NÃO INFORMADA"),
              "-".join(resumo["data_envio"].split("-")[::-1])]
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", " - ".join(partes).upper())


def gerar_pdf_faturamento(faturamento):
    resumo = faturamento.resumo
    usa_bep = resumo.get("usa_bep", fornecedor_usa_bep(resumo["fornecedor_nome"]))
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=14 * mm,
                            leftMargin=14 * mm, topMargin=14 * mm, bottomMargin=18 * mm,
                            title=titulo_faturamento(resumo), author="AGRO-AI-PRO")
    corpo = ParagraphStyle("Corpo", fontName="Helvetica", fontSize=9, leading=12, spaceAfter=5)
    titulo = ParagraphStyle("Titulo", parent=corpo, fontName="Helvetica-Bold", fontSize=17, leading=21, spaceAfter=9)
    cabecalho = ParagraphStyle("Cabecalho", parent=corpo, fontName="Helvetica-Bold", textColor=colors.white, spaceAfter=0)
    celula = ParagraphStyle("Celula", parent=corpo, spaceAfter=0)
    numerica = ParagraphStyle("Numero", parent=celula, alignment=TA_RIGHT)

    def p(texto, estilo=corpo):
        # Todos os textos vêm de cadastros: escapar impede interpretar marcação ou recursos externos.
        return Paragraph(escape(str(texto or "Não informado")).replace("\n", "<br/>"), estilo)

    destaque = ParagraphStyle("Destaque", parent=celula, fontName="Helvetica-Bold")
    dados_cabecalho = Table([
        [[p("Empresa destinatária", celula), p(resumo["fornecedor_nome"], destaque)],
         [p(f"Total de embalagens: {numero(resumo['total_embalagens'])}", destaque), p(f"{resumo['embalagem']} de {numero(resumo['conteudo_embalagem'])} {resumo['unidade']}", celula)],
         [p("Data do envio", celula), p(f"{faturamento.data_envio:%d/%m/%Y}", destaque)]],
        [[p("Produto", celula), p(resumo["produto_nome"], destaque)],
         [p(f"Quantidade total: {numero(resumo['quantidade_total'])} {resumo['unidade']}", destaque), p(f"Dosagem: {numero(resumo['dosagem_alqueire'])} {resumo['unidade']}/alq.", celula)],
         [p("Safra", celula), p(resumo.get("safra") or "Não informada", destaque)]],
    ], colWidths=[115 * mm, 95 * mm, 59 * mm], hAlign="LEFT")
    dados_cabecalho.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("BACKGROUND", (0, 0), (1, 0), colors.HexColor("#EDF3EF")),
        ("LINEABOVE", (0, 0), (-1, 0), 0.5, colors.HexColor("#DDE4DE")),
        ("LINEBELOW", (0, -1), (-1, -1), 0.5, colors.HexColor("#DDE4DE")),
    ]))
    conteudo = [p("Faturamento de insumos", titulo), dados_cabecalho, Spacer(1, 4 * mm)]
    titulos = ["Propriedade", "Produtor", "CAD/PRO"]
    larguras = [60, 41, 30]
    if usa_bep:
        titulos.append("BEP")
        larguras.append(32)
    else:
        larguras[0] += 20
        larguras[1] += 12
    titulos += ["Área (alq.)", "Embalagens", f"Quantidade ({resumo['unidade']})"]
    larguras += [27, 32, 47]
    linhas = [[p(t, cabecalho) for t in titulos]]
    for item in resumo["itens"]:
        lat = item.get('latitude_gms') if item.get('formato_coordenadas')=='gms' else item.get('latitude')
        lon = item.get('longitude_gms') if item.get('formato_coordenadas')=='gms' else item.get('longitude')
        posicao = f'Latitude: {lat}\nLongitude: {lon}' if lat is not None and lon is not None and lat!='' and lon!='' else 'Coordenadas não informadas'
        linha = [p(item["propriedade_nome"]+'\n'+posicao, celula), p(item["produtor"], celula), p(item["cad_pro"], celula)]
        if usa_bep:
            linha.append(p(item.get("bep", ""), celula))
        linha += [p(numero(item[campo]), numerica) for campo in ("area_alqueires", "quantidade_embalagens", "quantidade")]
        linhas.append(linha)
    total = [p("Total", celula)] + [""] * (len(titulos) - 4)
    total += [p(numero(sum(Decimal(i["area_alqueires"]) for i in resumo["itens"])), numerica),
              p(numero(resumo["total_embalagens"]), numerica), p(numero(resumo["quantidade_total"]), numerica)]
    linhas.append(total)
    tabela = LongTable(linhas, colWidths=[v * mm for v in larguras], repeatRows=1, hAlign="LEFT")
    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#24543E")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 1), (-1, -2), 0.4, colors.HexColor("#DDE4DE")),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#EDF3EF")),
        ("LINEABOVE", (0, -1), (-1, -1), 0.8, colors.HexColor("#24543E")),
    ]))
    conteudo.append(tabela)
    if resumo.get("observacoes"):
        conteudo += [Spacer(1, 5 * mm), p("Observações: " + resumo["observacoes"])]

    def rodape(canvas, document):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#506058"))
        canvas.drawString(14 * mm, 9 * mm, f"AGRO-AI-PRO | Protocolo {faturamento.id}")
        canvas.drawRightString(283 * mm, 9 * mm, f"Página {document.page}")
        canvas.restoreState()

    doc.build(conteudo, onFirstPage=rodape, onLaterPages=rodape)
    return buffer.getvalue()

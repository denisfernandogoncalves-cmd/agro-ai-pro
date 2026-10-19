"""PDF individual a partir do snapshot, sem consultar cadastros alterados depois do envio."""
from decimal import Decimal
from io import BytesIO
import re
import os
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, LongTable, Paragraph, SimpleDocTemplate, Spacer, TableStyle

from .faturamento import fornecedor_usa_bep


def registrar_arial():
    """Fontes locais licenciadas; não distribuir arquivos de fonte no repositório."""
    if "Arial" in pdfmetrics.getRegisteredFontNames():
        return
    pastas = [Path(os.environ.get("AGRO_ARIAL_DIR", "/app/.fonts")),
              Path(__file__).resolve().parents[3] / ".fonts", Path("C:/Windows/Fonts")]
    for pasta in pastas:
        if (pasta / "arial.ttf").is_file() and (pasta / "arialbd.ttf").is_file():
            pdfmetrics.registerFont(TTFont("Arial", str(pasta / "arial.ttf")))
            pdfmetrics.registerFont(TTFont("Arial-Bold", str(pasta / "arialbd.ttf")))
            return
    raise RuntimeError("Instale arial.ttf e arialbd.ttf e configure AGRO_ARIAL_DIR para gerar o faturamento em Arial.")


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
    registrar_arial()
    resumo = faturamento.resumo
    usa_bep = resumo.get("usa_bep", fornecedor_usa_bep(resumo["fornecedor_nome"]))
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=14 * mm,
                            leftMargin=14 * mm, topMargin=14 * mm, bottomMargin=25 * mm,
                            title=titulo_faturamento(resumo), author="AGRO-AI-PRO")
    corpo = ParagraphStyle("Corpo", fontName="Arial", fontSize=12, leading=16, spaceAfter=5)
    titulo = ParagraphStyle("Titulo", parent=corpo, fontName="Arial-Bold", spaceAfter=10)
    rotulo = ParagraphStyle("Rotulo", parent=titulo, spaceAfter=0)

    def p(texto, estilo=corpo):
        return Paragraph(escape(str(texto if texto is not None and texto != "" else "Não informado")).replace("\n", "<br/>"), estilo)

    def tabela(campos):
        # Duas colunas mantêm o tamanho da fonte sem reduzir a escala da página.
        t = LongTable([[p(campo, rotulo), p(valor)] for campo, valor in campos],
                      colWidths=[62 * mm, 120 * mm], hAlign="LEFT")
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#DDE4DE")),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EDF3EF")),
        ]))
        return t

    conteudo = [p("Faturamento de insumos", titulo), tabela([
        ("Empresa destinatária", resumo["fornecedor_nome"]),
        ("Produto", resumo["produto_nome"]),
        ("Data do envio", f"{faturamento.data_envio:%d/%m/%Y}"),
        ("Safra", resumo.get("safra") or "Não informada"),
        ("Apresentação", f"{resumo['embalagem']} de {numero(resumo['conteudo_embalagem'])} {resumo['unidade']}"),
        ("Dosagem", f"Dosagem: {numero(resumo['dosagem_alqueire'])} {resumo['unidade']}/alq."),
    ])]
    cabecalhos = ["Propriedade / produtor", "CAD/PRO", "Área (alq.)", "Emb.", f"Qtd. ({resumo['unidade']})"]
    linhas = [[p(texto, rotulo) for texto in cabecalhos]]
    for item in resumo["itens"]:
        lat = item.get('latitude_gms') if item.get('formato_coordenadas') == 'gms' else item.get('latitude')
        lon = item.get('longitude_gms') if item.get('formato_coordenadas') == 'gms' else item.get('longitude')
        propriedade = (f"{item['propriedade_nome']}\nProdutor: {item.get('produtor') or 'Não informado'}"
                       f"\nLatitude: {lat if lat is not None and lat != '' else 'Não informada'}"
                       f"\nLongitude: {lon if lon is not None and lon != '' else 'Não informada'}")
        cadastro = f"{item.get('cad_pro') or 'Não informado'}\nIdentificação: {item.get('cad_pro_identificacao') or 'Não informado'}"
        if usa_bep:
            cadastro += f"\nBEP: {item.get('bep') or 'Não informado'}"
        linhas.append([p(propriedade), p(cadastro)] + [p(numero(item[campo]))
                       for campo in ('area_alqueires', 'quantidade_embalagens', 'quantidade')])
    grade = LongTable(linhas, colWidths=[68 * mm, 42 * mm, 22 * mm, 25 * mm, 25 * mm],
                     repeatRows=1, hAlign="LEFT")
    grade.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EDF3EF")),
        ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#DDE4DE")),
    ]))
    conteudo += [Spacer(1, 5 * mm), grade]
    conteudo += [KeepTogether([Spacer(1, 5 * mm),
                 p(f"Área total (alq.): {numero(sum(Decimal(i['area_alqueires']) for i in resumo['itens']))}", titulo),
                 p(f"Total de embalagens: {numero(resumo['total_embalagens'])}", titulo),
                 p(f"Quantidade total: {numero(resumo['quantidade_total'])} {resumo['unidade']}", titulo)])]
    if resumo.get("observacoes"):
        conteudo += [p("Observações: " + resumo["observacoes"])]

    def rodape(canvas, document):
        canvas.saveState()
        canvas.setFont("Arial", 12)
        canvas.setFillColor(colors.HexColor("#506058"))
        canvas.drawString(14 * mm, 17 * mm, f"Protocolo {faturamento.id}")
        canvas.drawString(14 * mm, 9 * mm, "AGRO-AI-PRO")
        canvas.drawRightString(196 * mm, 9 * mm, f"Página {document.page}")
        canvas.restoreState()

    doc.build(conteudo, onFirstPage=rodape, onLaterPages=rodape)
    return buffer.getvalue()

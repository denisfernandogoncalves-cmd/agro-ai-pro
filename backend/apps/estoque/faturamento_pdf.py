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


def descricao_embalagens(resumo):
    nomes = {
        'balde': ('BALDE', 'BALDES'), 'baldes': ('BALDE', 'BALDES'),
        'galão': ('GALÃO', 'GALÕES'), 'galões': ('GALÃO', 'GALÕES'),
        'saco': ('SACO', 'SACOS'), 'sacos': ('SACO', 'SACOS'),
        'caixa': ('CAIXA', 'CAIXAS'), 'caixas': ('CAIXA', 'CAIXAS'),
        'frasco': ('FRASCO', 'FRASCOS'), 'frascos': ('FRASCO', 'FRASCOS'),
        'pacote': ('PACOTE', 'PACOTES'), 'pacotes': ('PACOTE', 'PACOTES'),
        'tambor': ('TAMBOR', 'TAMBORES'), 'tambores': ('TAMBOR', 'TAMBORES'),
    }
    unidades = {'l': ('LITRO', 'LITROS'), 'ml': ('MILILITRO', 'MILILITROS'),
                'kg': ('QUILOGRAMA', 'QUILOGRAMAS'), 'g': ('GRAMA', 'GRAMAS'),
                't': ('TONELADA', 'TONELADAS'), 'un': ('UNIDADE', 'UNIDADES')}
    embalagem = resumo['embalagem'].strip()
    nome = nomes.get(embalagem.casefold(), (embalagem.upper(), embalagem.upper()))[Decimal(resumo['total_embalagens']) != 1]
    unidade = resumo['unidade'].strip()
    medida = unidades.get(unidade.casefold(), (unidade.upper(), unidade.upper()))[Decimal(resumo['conteudo_embalagem']) != 1]
    return f"{numero(resumo['total_embalagens'])} {nome} DE {numero(resumo['conteudo_embalagem'])} {medida}"


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

    linha_principal = (f"{resumo['produto_nome']} · Total de embalagens: {descricao_embalagens(resumo)}"
                       f" · Quantidade total: {numero(resumo['quantidade_total'])} {resumo['unidade']}")
    linha_detalhes = (f"{resumo['fornecedor_nome']} · {faturamento.data_envio:%d/%m/%Y}"
                     f" · Safra: {resumo.get('safra') or 'Não informada'}"
                     f" · Dosagem: {numero(resumo['dosagem_alqueire'])} {resumo['unidade']}/alq.")
    dados_cabecalho = LongTable([[p(linha_principal, rotulo)], [p(linha_detalhes)]],
                               colWidths=[182 * mm], hAlign="LEFT")
    dados_cabecalho.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EDF3EF")),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW", (0, -1), (-1, -1), 0.5, colors.HexColor("#DDE4DE")),
    ]))
    conteudo = [p("Faturamento de insumos", titulo), dados_cabecalho]
    cabecalhos = ["Propriedade / produtor", "CAD/PRO", "Área (alq.)", "Emb.", f"Qtd. ({resumo['unidade']})"]
    linhas = [[p(texto, rotulo) for texto in cabecalhos]]
    for item in resumo["itens"]:
        lat = item.get('latitude_gms') if item.get('formato_coordenadas') == 'gms' else item.get('latitude')
        lon = item.get('longitude_gms') if item.get('formato_coordenadas') == 'gms' else item.get('longitude')
        propriedade = f"{item['propriedade_nome']}\nProdutor: {item.get('produtor') or 'Não informado'}"
        coordenadas = (f"Latitude: {lat if lat is not None and lat != '' else 'Não informada'}"
                       f" · Longitude: {lon if lon is not None and lon != '' else 'Não informada'}")
        tamanho_coordenadas = min(9, 12 * (82 * mm - 8) / pdfmetrics.stringWidth(coordenadas, "Arial", 12))
        estilo_coordenadas = ParagraphStyle("Coordenadas", parent=corpo, fontSize=tamanho_coordenadas,
                                            leading=tamanho_coordenadas * 1.3, spaceAfter=0)
        cadastro = f"{item.get('cad_pro') or 'Não informado'}\nIdentificação: {item.get('cad_pro_identificacao') or 'Não informado'}"
        if usa_bep:
            cadastro += f"\nBEP: {item.get('bep') or 'Não informado'}"
        linhas.append([[p(propriedade), p(coordenadas, estilo_coordenadas)], p(cadastro)] + [p(numero(item[campo]))
                       for campo in ('area_alqueires', 'quantidade_embalagens', 'quantidade')])
    grade = LongTable(linhas, colWidths=[82 * mm, 36 * mm, 20 * mm, 22 * mm, 22 * mm],
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
                 p(f"Total de embalagens: {descricao_embalagens(resumo)}", titulo),
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

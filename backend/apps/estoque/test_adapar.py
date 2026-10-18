import io
from unittest.mock import patch

from django.test import SimpleTestCase
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet

from .adapar import ConsultaIndisponivel, extrair


class LeituraAdaparTests(SimpleTestCase):
    def documento(self, cabecalho="Atualização: 09/10/2026 — INGREDIENTE ATIVO"):
        arquivo = io.BytesIO()
        estilo = getSampleStyleSheet()["Normal"]
        elementos = []
        for nome in ("OUTRO PRODUTO", "FOLICUR 200 EC", "OUTRO PRODUTO FINAL"):
            tabela = Table([[nome, "BAYER", "FUNGICIDA", "TEBUCONAZOL", "200 g/L", "2895", "Cat.5"]], colWidths=[105, 40, 65, 90, 50, 40, 35])
            tabela.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), .5, colors.black), ("FONTSIZE", (0, 0), (-1, -1), 7)]))
            if elementos:
                elementos.append(PageBreak())
            elementos.extend([Paragraph(cabecalho, estilo), tabela])
        SimpleDocTemplate(arquivo).build(elementos)
        return arquivo.getvalue()

    def test_localiza_pagina_e_extrai_campos_sem_layout_do_documento_inteiro(self):
        import pdfplumber.page
        original = pdfplumber.page.Page.extract_tables
        paginas = []

        def tabelas(pagina, *args, **kwargs):
            paginas.append(pagina.page_number)
            return original(pagina, *args, **kwargs)

        with patch.object(pdfplumber.page.Page, "extract_text", side_effect=AssertionError("Não deve analisar layout de texto de todas as páginas")), patch.object(pdfplumber.page.Page, "extract_tables", tabelas):
            itens = extrair(self.documento(), "FOLICUR", "https://www.adapar.pr.gov.br/lista.pdf")
        self.assertEqual(paginas, [2])
        self.assertEqual(len(itens), 1)
        self.assertEqual(itens[0]["nome"], "FOLICUR 200 EC")
        self.assertEqual(itens[0]["principios_ativos"], "TEBUCONAZOL")
        self.assertEqual(itens[0]["registro_mapa"], "2895")
        self.assertEqual(itens[0]["atualizacao_fonte"], "09/10/2026")

    def test_nome_ausente_nao_extrai_tabelas(self):
        with patch("pdfplumber.page.Page.extract_tables", side_effect=AssertionError("Página sem o nome não deve ser analisada")):
            self.assertEqual(extrair(self.documento(), "INEXISTENTE", "fonte"), [])

    def test_publicacao_sem_cabecalho_reconhecido_e_rejeitada(self):
        with self.assertRaises(ConsultaIndisponivel):
            extrair(self.documento("Documento desconhecido"), "FOLICUR", "fonte")

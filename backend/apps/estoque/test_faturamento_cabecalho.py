from datetime import date
from io import BytesIO
from types import SimpleNamespace

import pdfplumber
from django.test import SimpleTestCase

from .faturamento_pdf import gerar_pdf_faturamento


def faturamento_teste(empresa="EMPRESA DEMONSTRAÇÃO"):
    return SimpleNamespace(id="demonstracao-sem-dados-reais", data_envio=date(2026, 10, 15), resumo={
        "fornecedor_nome":empresa, "produto_nome":"PRODUTO DEMONSTRAÇÃO", "data_envio":"2026-10-15",
        "embalagem":"GALÕES", "conteudo_embalagem":"5", "unidade":"l", "safra":"26-27",
        "dosagem_alqueire":"0.25", "total_embalagens":"2", "quantidade_total":"10", "usa_bep":False,
        "itens":[{"propriedade_nome":f"Propriedade exemplo {i}", "produtor":"Produtor exemplo", "cad_pro":"EXEMPLO",
            "area_alqueires":area, "quantidade_embalagens":"1", "quantidade":"5"} for i, area in ((1,"1.450413"),(2,"3.752066"))],
    })


class CabecalhoFaturamentoTests(SimpleTestCase):
    def test_distribui_empresa_embalagens_e_data_sem_aumentar_fontes(self):
        with pdfplumber.open(BytesIO(gerar_pdf_faturamento(faturamento_teste()))) as pdf:
            self.assertEqual(len(pdf.pages), 1)
            pagina = pdf.pages[0]
            texto = pagina.extract_text()
            for esperado in ("EMPRESA DEMONSTRAÇÃO", "Total de embalagens: 2", "GALÕES de 5 l", "15/10/2026", "26-27", "Dosagem: 0,25 l/alq."):
                self.assertIn(esperado, texto)
            palavras = pagina.extract_words()
            empresa = next(p for p in palavras if p["text"] == "Empresa")
            embalagens = next(p for p in palavras if p["text"] == "Total")
            data = next(p for p in palavras if p["text"] == "Data")
            self.assertLess(abs(empresa["top"] - embalagens["top"]), 1)
            self.assertLess(abs(empresa["top"] - data["top"]), 1)
            self.assertLess(empresa["x0"], embalagens["x0"])
            self.assertLess(embalagens["x0"], data["x0"])
            self.assertLessEqual(max(c["size"] for c in pagina.chars), 17)
            self.assertTrue(all(c["x0"] >= 0 and c["x1"] <= pagina.width for c in pagina.chars))

    def test_texto_longo_quebra_sem_perder_tabela_ou_interpretar_html(self):
        nome = "Empresa & Companhia <b>literal</b> " + "Nome extenso " * 12
        with pdfplumber.open(BytesIO(gerar_pdf_faturamento(faturamento_teste(nome)))) as pdf:
            self.assertEqual(len(pdf.pages), 1)
            texto = pdf.pages[0].extract_text()
            self.assertIn("<b>literal</b>", texto)
            self.assertIn("Propriedade exemplo 2", texto)
            self.assertIn("Página 1", texto)

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
            self.assertGreaterEqual(len(pdf.pages), 1)
            pagina = pdf.pages[0]
            texto = '\n'.join(p.extract_text() for p in pdf.pages)
            for esperado in ("EMPRESA DEMONSTRAÇÃO", "Total de embalagens: 2", "2 GALÕES DE 5 LITROS", "15/10/2026", "26-27", "Dosagem: 0,25 l/alq."):
                self.assertIn(esperado, ' '.join(texto.split()))
            for pagina in pdf.pages:
                self.assertAlmostEqual(pagina.width, 595.276, places=2)
                self.assertAlmostEqual(pagina.height, 841.890, places=2)
                self.assertTrue(all(6 <= c['size'] <= 12.01 and 'Arial' in c['fontname'] for c in pagina.chars))
                self.assertTrue(all(c['x0'] >= 0 and c['x1'] <= pagina.width for c in pagina.chars))

    def test_texto_longo_quebra_sem_perder_tabela_ou_interpretar_html(self):
        nome = "Empresa & Companhia <b>literal</b> " + "Nome extenso " * 12
        with pdfplumber.open(BytesIO(gerar_pdf_faturamento(faturamento_teste(nome)))) as pdf:
            self.assertGreaterEqual(len(pdf.pages), 1)
            texto = '\n'.join(p.extract_text() for p in pdf.pages)
            self.assertIn("<b>literal</b>", texto)
            self.assertIn("Propriedade exemplo 2", texto)
            self.assertIn("Página 1", texto)

    def test_excel_a4_retrato_arial12(self):
        from openpyxl import load_workbook
        from .faturamento_excel import exportar_excel_faturamento
        registro = faturamento_teste()
        registro.pk = registro.id
        registro.resumo['usa_bep'] = True
        registro.resumo['itens'][0].update(cad_pro='00123', cad_pro_identificacao='Principal', bep='00456')
        wb = load_workbook(BytesIO(exportar_excel_faturamento(registro).content))
        self.assertEqual(wb.active.title, 'Impressão')
        self.assertTrue(wb.active['A2'].value.startswith(registro.resumo['produto_nome']))
        for endereco in ('A2',):
            self.assertTrue(wb.active[endereco].font.bold)
        self.assertIn('Total de embalagens:', wb.active['A2'].value)
        self.assertIn('Quantidade total:', wb.active['A2'].value)
        linha = next(l for l in wb.active.values if l[0] and 'Propriedade exemplo 1' in str(l[0]))
        self.assertIn('Principal', linha[1])
        self.assertEqual(linha[3], 1)
        self.assertEqual(linha[4], 5)
        for esperado in ('Principal', '00123', '00456', 'Propriedade exemplo 2'):
            self.assertIn(esperado, str(list(wb.active.values)))
        for aba in wb:
            self.assertEqual(str(aba.page_setup.paperSize), str(aba.PAPERSIZE_A4))
            self.assertEqual(aba.page_setup.orientation, aba.ORIENTATION_PORTRAIT)
            self.assertEqual(aba.page_setup.scale, 100)
            self.assertTrue(aba.print_area)
            for linha in aba:
                for celula in linha:
                    if celula.value is None:
                        continue
                    self.assertEqual(celula.font.name, 'Arial')
                    self.assertEqual(celula.font.sz, 12)
                    self.assertTrue(celula.alignment.wrap_text)

    def test_propriedades_em_linhas_com_colunas_numericas(self):
        with pdfplumber.open(BytesIO(gerar_pdf_faturamento(faturamento_teste()))) as pdf:
            palavras = [p for pagina in pdf.pages for p in pagina.extract_words()]
            propriedades = [p for p in palavras if p['text'] == 'Propriedade']
            self.assertGreaterEqual(len(propriedades), 2)
            self.assertAlmostEqual(propriedades[-1]['x0'], propriedades[-2]['x0'], places=1)
            self.assertTrue(any(p['text'] == 'Emb.' and p['x0'] > 350 for p in palavras))

    def test_cabecalho_produto_primeiro_e_coordenadas_na_mesma_linha(self):
        registro = faturamento_teste()
        registro.resumo['itens'][0].update(formato_coordenadas='gms', latitude_gms='24°18\'28,98"S', longitude_gms='51°42\'48,71"O')
        with pdfplumber.open(BytesIO(gerar_pdf_faturamento(registro))) as pdf:
            pagina = pdf.pages[0]
            texto = pagina.extract_text()
            self.assertLess(texto.index('PRODUTO DEMONSTRAÇÃO'), texto.index('Total de embalagens:'))
            self.assertLess(texto.index('PRODUTO DEMONSTRAÇÃO'), texto.index('Quantidade total:'))
            palavras = pagina.extract_words()
            lat = next(p for p in palavras if p['text'] == 'Latitude:')
            lon = next(p for p in palavras if p['text'] == 'Longitude:')
            self.assertAlmostEqual(lat['top'], lon['top'], places=1)
            self.assertLess(lat['x0'], lon['x0'])

    def test_cabecalho_em_duas_linhas_para_dados_da_tela(self):
        registro = faturamento_teste('AGRO PRODUZ')
        registro.resumo.update(produto_nome='ANKOR', total_embalagens='7', quantidade_total='140',
                              embalagem='Balde', conteudo_embalagem='20', dosagem_alqueire='5')
        with pdfplumber.open(BytesIO(gerar_pdf_faturamento(registro))) as pdf:
            linhas = pdf.pages[0].extract_text().splitlines()
            self.assertTrue(linhas[1].startswith('ANKOR'))
            self.assertIn('Total de embalagens: 7', linhas[1])
            self.assertIn('Quantidade total: 140 l', linhas[1])
            self.assertIn('AGRO PRODUZ', linhas[2])
            self.assertIn('Dosagem: 5 l/alq.', linhas[2])
            self.assertTrue(linhas[3].startswith('Propriedade'))

    def test_descricao_completa_embalagens(self):
        from .faturamento_pdf import descricao_embalagens
        resumo = faturamento_teste().resumo
        resumo.update(embalagem='BALDES', total_embalagens='7', conteudo_embalagem='20', unidade='l')
        self.assertEqual(descricao_embalagens(resumo), '7 BALDES DE 20 LITROS')
        resumo.update(total_embalagens='1', conteudo_embalagem='1')
        self.assertEqual(descricao_embalagens(resumo), '1 BALDE DE 1 LITRO')
        resumo.update(embalagem='Pacote', total_embalagens='2', conteudo_embalagem='2.5', unidade='kg')
        self.assertEqual(descricao_embalagens(resumo), '2 PACOTES DE 2,5 QUILOGRAMAS')

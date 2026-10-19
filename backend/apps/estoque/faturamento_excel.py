"""Excel individual a partir do resumo histórico do faturamento."""
from decimal import Decimal
from copy import copy
from math import ceil

from openpyxl.styles import Alignment
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.page import PageMargins

from apps.core.excel import PlanilhaExportacao
from .faturamento import fornecedor_usa_bep


def exportar_excel_faturamento(faturamento):
    resumo = faturamento.resumo
    planilha = PlanilhaExportacao('Faturamento de insumos')
    planilha.adicionar('Faturamento', ['Campo', 'Valor'], [
        ['Protocolo', str(faturamento.pk)], ['Empresa', resumo['fornecedor_nome']],
        ['Produto', resumo['produto_nome']], ['Data do envio', faturamento.data_envio],
        ['Safra', resumo.get('safra') or 'Não informada'], ['Embalagem', resumo['embalagem']],
        ['Conteúdo por embalagem', Decimal(resumo['conteudo_embalagem'])], ['Unidade', resumo['unidade']],
        ['Dosagem por alqueire', Decimal(resumo['dosagem_alqueire'])],
        ['Total de embalagens', Decimal(resumo['total_embalagens'])],
        ['Quantidade total', Decimal(resumo['quantidade_total'])], ['Observações', resumo.get('observacoes', '')],
    ])
    usa_bep = resumo.get('usa_bep', fornecedor_usa_bep(resumo['fornecedor_nome']))
    colunas = ['Propriedade', 'Produtor', 'CAD/PRO', 'Identificação CAD/PRO']
    if usa_bep:
        colunas.append('BEP')
    colunas += ['Área (alq.)', 'Embalagens', f'Quantidade ({resumo["unidade"]})']
    linhas = []
    for item in resumo['itens']:
        linha = [item['propriedade_nome'], item.get('produtor', ''), item.get('cad_pro', ''), item.get('cad_pro_identificacao') or 'Não informado']
        if usa_bep:
            linha.append(item.get('bep', ''))
        linha += [Decimal(item[campo]) for campo in ('area_alqueires', 'quantidade_embalagens', 'quantidade')]
        linhas.append(linha)
    folha = planilha.adicionar('Propriedades', colunas, linhas)
    folha.column_dimensions['A'].width = 45
    folha.column_dimensions['B'].width = 35
    folha.column_dimensions['D'].width = 30
    for linha in folha.iter_rows(min_row=2):
        linha[len(colunas) - 3].number_format = '#,##0.0000'
    # Uma propriedade por linha; produtor/coordenadas e identificação/BEP
    # compartilham células para caber em retrato sem diminuir a fonte.
    campos = [[campo, valor, '', '', ''] for campo, valor in list(planilha.workbook['Faturamento'].values)[1:]]
    cabecalho = len(campos) + 2
    campos.append(['Propriedade / produtor', 'CAD/PRO', 'Área (alq.)', 'Embalagens', f'Quantidade ({resumo["unidade"]})'])
    for item in resumo['itens']:
        propriedade = f"{item['propriedade_nome']}\nProdutor: {item.get('produtor') or 'Não informado'}"
        for eixo in ('latitude', 'longitude'):
            valor = item.get(eixo + '_gms') if item.get('formato_coordenadas') == 'gms' else item.get(eixo)
            propriedade += f"\n{eixo.capitalize()}: {valor if valor is not None and valor != '' else 'Não informada'}"
        cadastro = f"{item.get('cad_pro') or 'Não informado'}\nIdentificação: {item.get('cad_pro_identificacao') or 'Não informado'}"
        if usa_bep:
            cadastro += f"\nBEP: {item.get('bep') or 'Não informado'}"
        campos.append([propriedade, cadastro] + [Decimal(item[campo]) for campo in ('area_alqueires', 'quantidade_embalagens', 'quantidade')])
    campos.append(['Total', '', sum(Decimal(i['area_alqueires']) for i in resumo['itens']),
                   Decimal(resumo['total_embalagens']), Decimal(resumo['quantidade_total'])])
    impressao = planilha.adicionar('Impressão', ['Faturamento de insumos', '', '', '', ''], campos)
    impressao.merge_cells('A1:E1')
    for indice in range(2, cabecalho):
        impressao.merge_cells(start_row=indice, start_column=2, end_row=indice, end_column=5)
    for indice, largura in zip('ABCDE', (32, 21, 10, 12, 12)):
        impressao.column_dimensions[indice].width = largura
    for celula in impressao[cabecalho]:
        celula._style = copy(impressao['A1']._style)
    for linha in impressao.iter_rows(min_row=cabecalho + 1):
        linha[2].number_format = '#,##0.0000'
    impressao.auto_filter.ref = None
    planilha.workbook.move_sheet(impressao, offset=-len(planilha.workbook.worksheets) + 1)
    planilha.workbook.active = 0
    for aba in planilha.workbook:
        aba.page_setup.paperSize = aba.PAPERSIZE_A4
        aba.page_setup.orientation = aba.ORIENTATION_PORTRAIT
        aba.page_setup.scale = 100
        aba.sheet_properties.pageSetUpPr.fitToPage = False
        aba.page_margins = PageMargins(left=0.55, right=0.55, top=0.55, bottom=0.55)
        aba.print_options.horizontalCentered = True
        aba.print_title_rows = f'{cabecalho}:{cabecalho}' if aba == impressao else '1:1'
        aba.print_area = aba.dimensions
        if aba.max_column == 2:
            aba.column_dimensions['A'].width = 28
            aba.column_dimensions['B'].width = 55
        for linha in aba:
            altura = 1
            for celula in linha:
                fonte = copy(celula.font)
                fonte.name, fonte.sz = 'Arial', 12
                celula.font = fonte
                celula.alignment = Alignment(wrap_text=True, vertical='top')
                largura = aba.column_dimensions[get_column_letter(celula.column)].width
                if aba == impressao and celula.column == 2 and celula.row < cabecalho:
                    largura = 55
                altura = max(altura, sum(max(1, ceil(len(parte) / max(1, int(largura * 0.75))))
                                        for parte in str(celula.value or '').split('\n')))
                if celula.column == 2 and linha[0].value == 'Área (alq.)':
                    celula.number_format = '#,##0.0000'
            aba.row_dimensions[linha[0].row].height = 18 * altura + 6
    return planilha.resposta('faturamento-insumos')

"""Preenche BP da coluna G da C.Vale usando a associação auditada da linha."""
import json
import re
from collections import defaultdict
from django.db import transaction
from apps.importacoes.models import LinhaImportacao, LoteImportacao
from apps.propriedades.models import Propriedade

aplicar = globals().get('INSUMOS_APLICAR', False)
resultado = {'modo': 'aplicado' if aplicar else 'ensaio com rollback', 'atualizados': [], 'preservados': [], 'pendentes': []}
with transaction.atomic():
    lote = LoteImportacao.objects.select_for_update().get(arquivo_nome='CVALE.xlsx',status='historico')
    candidatos = defaultdict(list)
    linhas = list(lote.linhas.filter(planilha='INSUMOS').order_by('linha_origem'))
    for linha in linhas:
        n = linha.linha_origem
        raw = linha.dados_originais.get('G'+str(n),{}).get('valor')
        if n < 8 or raw in (None,''):
            continue
        codigo = str(raw).strip()
        if re.fullmatch(r'\d+\.0+',codigo):
            codigo = codigo.split('.')[0]
        if not re.fullmatch(r'\d{1,40}',codigo):
            resultado['pendentes'].append({'linha':n,'bp':codigo,'motivo':'BP inválido'})
            continue
        if not linha.propriedade_id:
            resultado['pendentes'].append({'linha':n,'bp':codigo,'motivo':'Propriedade ainda não associada'})
            continue
        candidatos[linha.propriedade_id].append((linha,codigo))
    for pk,itens in candidatos.items():
        p = Propriedade.objects.select_for_update().get(pk=pk)
        codigos = {codigo for _,codigo in itens}
        if len(codigos)!=1:
            resultado['pendentes'].append({'propriedade':p.nome,'codigos':sorted(codigos),'motivo':'BPs distintos para a mesma propriedade'})
            continue
        codigo = codigos.pop()
        if p.bp_cvale and p.bp_cvale != codigo:
            resultado['pendentes'].append({'propriedade':p.nome,'existente':p.bp_cvale,'planilha':codigo,'motivo':'BP existente preservado; divergência'})
            continue
        if p.bp_cvale == codigo:
            resultado['preservados'].append({'id':p.pk,'propriedade':p.nome,'bp':codigo})
        else:
            p.bp_cvale = codigo
            Propriedade._meta.get_field('bp_cvale').clean(codigo,p)
            p.save(update_fields=['bp_cvale'])
            p.refresh_from_db()
            assert p.bp_cvale == codigo
            resultado['atualizados'].append({'id':p.pk,'propriedade':p.nome,'bp':codigo})
        for linha,codigo in itens:
            linha.dados_normalizados = {**linha.dados_normalizados,'bp_cvale':codigo}
            linha.save(update_fields=['dados_normalizados'])
    lote.metadados = {**lote.metadados,'bp_cvale_importado':resultado}
    lote.save(update_fields=['metadados'])
    if not aplicar:
        transaction.set_rollback(True)
print(json.dumps(resultado,ensure_ascii=False))

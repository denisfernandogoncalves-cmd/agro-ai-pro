"""Importação auditável das fontes extraídas; executar pelo shell Django.

Recebe INSUMOS_PAYLOAD no ambiente global. INSUMOS_APLICAR=False faz ensaio
com rollback integral. Não cria dívidas nem altera saldos de estoque/grãos.
"""
import hashlib
import json
import unicodedata
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.contrib.auth import get_user_model
from django.db import transaction, connection
from apps.propriedades.models import Propriedade
from apps.estoque.models import ProdutoEstoque, MovimentacaoEstoque
from apps.financeiro.models import ParceiroFinanceiro, LancamentoFinanceiro
from apps.cadpro.models import CADPro, CADProPropriedade
from apps.importacoes.models import LoteImportacao, LinhaImportacao


def texto(v):
    return ' '.join(str(v or '').split())


def chave(v):
    t = unicodedata.normalize('NFKD', texto(v))
    return ''.join(c for c in t if not unicodedata.combining(c)).upper()


def decimal(v):
    try:
        d = Decimal(str(v))
        return d if d.is_finite() else None
    except (InvalidOperation, ValueError, TypeError):
        return None


def linhas(fonte, aba):
    for a in fonte['abas']:
        if a['resumo']['aba'] == aba:
            for cells in a['celulas']:
                n = int(next(iter(cells))[1:])
                yield n, {c.rstrip('0123456789'): v['valor'] for c, v in cells.items()}


def salvar(obj):
    obj.full_clean()
    obj.save()
    return obj


payload = INSUMOS_PAYLOAD
aplicar = globals().get('INSUMOS_APLICAR', False)
usuario = get_user_model().objects.get(username='DENIS', is_active=True, is_superuser=True)
resultado = {'modo': 'aplicado' if aplicar else 'ensaio com rollback', 'criados': Counter(), 'reutilizados': Counter(), 'pendencias': [], 'lotes': []}


def pendencia(entidade, nome, motivo, **origem):
    resultado['pendencias'].append({'entidade': entidade, 'nome': nome, 'motivo': motivo, **origem})


with transaction.atomic():
    if connection.vendor == 'postgresql':
        with connection.cursor() as c:
            c.execute('SELECT pg_advisory_xact_lock(%s)', [202610091])
    antes = (MovimentacaoEstoque.objects.count(), LancamentoFinanceiro.objects.count())
    fontes_novas = [f for f in payload['fontes'] if not LoteImportacao.objects.filter(arquivo_sha256=f['sha256']).exists()]
    coords = {(r['fonte'], r['linha']): r for r in payload['coordenadas']['linhas']}
    props = defaultdict(list)
    for p in Propriedade.objects.all():
        props[chave(p.nome)].append(p)
    candidatos = defaultdict(list)
    for f in fontes_novas:
        if f['nome'] == 'ESTOQUE .xlsx':
            continue
        for n, r in linhas(f, 'INSUMOS'):
            if n < 8 or not isinstance(r.get('A'), (int, float)):
                continue
            nome = texto(r.get('F'))
            if not nome:
                if texto(r.get('D')):
                    pendencia('propriedade', texto(r.get('D')), 'Nome oficial ausente; apelido preservado no histórico.', fonte=f['nome'], linha=n)
                continue
            coord = coords.get((f['json_nome'], n), {})
            produtor = texto(r.get('J' if f['nome']=='CVALE.xlsx' else 'I'))
            produtor = 'CLAUDINEI SILVESTRE' if chave(produtor)=='NEI' else produtor
            area = decimal(r.get('C' if f['nome']=='CVALE.xlsx' else 'B'))
            cad = texto(r.get('K' if f['nome']=='CVALE.xlsx' else 'J'))
            bp = texto(r.get('G')) if f['nome']=='CVALE.xlsx' else ''
            candidatos[chave(nome)].append({'nome':nome,'area':area,'produtor':produtor,'cad':cad,'bp':bp,'coord':coord,'fonte':f['nome'],'linha':n})
    # Entre fornecedores, o mesmo cadastro pode ter nomes ligeiramente distintos.
    # Só unir quando TODOS os dados e o ponto coincidem e há uma linha por fonte.
    assinaturas = defaultdict(list)
    for k, itens in candidatos.items():
        for item in itens:
            c = item['coord']
            if item['area'] and c.get('municipio'):
                assinaturas[(item['area'],item['produtor'],item['cad'],c.get('latitude'),c.get('longitude'))].append((k,item))
    for pares in assinaturas.values():
        ks = {k for k,_ in pares}
        contagem = Counter(i['fonte'] for _,i in pares)
        if len(ks)>1 and len(contagem)==2 and all(v==1 for v in contagem.values()):
            destino = min(ks,key=lambda k:len(candidatos[k][0]['nome']))
            for k in ks-{destino}:
                if k in candidatos and destino in candidatos:
                    candidatos[destino].extend(candidatos.pop(k))
    associacoes = {}
    for k, registros in candidatos.items():
        r = registros[0]
        existentes = props.get('SAGRILO' if k=='SITIO SAGRILO' else k, [])
        if len(existentes)>1:
            pendencia('propriedade',r['nome'],'Mais de um cadastro existente com este nome.')
            continue
        if existentes:
            p = existentes[0]
            resultado['reutilizados']['propriedades'] += 1
            for item in registros:
                if item['area'] and (item['area']*Decimal('2.42')).quantize(Decimal('.01'),rounding=ROUND_HALF_UP) != p.area_hectares:
                    pendencia('area',p.nome,'Área existente preservada; diverge da planilha.',fonte=item['fonte'],linha=item['linha'],area_existente_ha=str(p.area_hectares),area_planilha_alq=str(item['area']))
        else:
            areas = {item['area'] for item in registros if item['area'] is not None}
            municipios = {item['coord'].get('municipio') for item in registros if item['coord'].get('municipio')}
            produtores = {item['produtor'] for item in registros if item['produtor']}
            pontos = {(item['coord'].get('latitude'),item['coord'].get('longitude')) for item in registros if item['coord'].get('municipio')}
            if len(areas)!=1 or next(iter(areas),Decimal('0'))<=0 or len(municipios)!=1 or len(produtores)>1 or len(pontos)!=1:
                pendencia('propriedade',r['nome'],'Área, produtor ou coordenadas ausentes/divergentes; cadastro pendente.',fontes=[{'arquivo':i['fonte'],'linha':i['linha']} for i in registros])
                continue
            latitude, longitude = next(iter(pontos))
            p = Propriedade(nome=r['nome'],proprietario=next(iter(produtores),''),municipio=next(iter(municipios)),uf='PR',area_hectares=(next(iter(areas))*Decimal('2.42')).quantize(Decimal('.01'),rounding=ROUND_HALF_UP),latitude=Decimal(str(latitude)).quantize(Decimal('.000001')),longitude=Decimal(str(longitude)).quantize(Decimal('.000001')),observacoes='Importado das planilhas de insumos. Área original em alqueires paulistas (2,42 ha). Município identificado pelo ponto na malha simplificada IBGE. Apelidos e CAD/PRO originais preservados em Importações.')
            if len(p.nome)>100:
                pendencia('propriedade',r['nome'],'Nome excede 100 caracteres; preservado integralmente no histórico.')
                continue
            salvar(p)
            props[k].append(p)
            resultado['criados']['propriedades'] += 1
        for item in registros:
            associacoes[(item['fonte'],item['linha'])] = p
            if item['bp'] and hasattr(p,'bp_cvale'):
                bp = item['bp'][:-2] if item['bp'].endswith('.0') else item['bp']
                if bp.isdigit() and (not p.bp_cvale or p.bp_cvale==bp):
                    Propriedade._meta.get_field('bp_cvale').clean(bp,p)
                    p.bp_cvale = bp
                    p.save(update_fields=['bp_cvale'])
                else:
                    pendencia('bp_cvale',p.nome,'BP inválido ou divergente do cadastro; valor existente preservado.',planilha=bp)
            if not item['cad']:
                continue
            cadcodigo = item['cad']
            if cadcodigo.endswith('.0'):
                cadcodigo = cadcodigo[:-2]
            antigos = set(p.vinculos_cadpro.filter(ativo=True).values_list('cad_pro__codigo', flat=True))
            if antigos and cadcodigo not in antigos:
                pendencia('cadpro',p.nome,'CAD/PRO existente difere da fonte; nenhum vínculo foi substituído.',existentes=sorted(antigos),planilha=cadcodigo)
                continue
            cad = CADPro.objects.filter(codigo=cadcodigo).first()
            if cad is None:
                cad = salvar(CADPro(codigo=cadcodigo,descricao='CAD/PRO importado das planilhas de insumos'))
                resultado['criados']['cadpro'] += 1
            if not cad.ativo:
                pendencia('cadpro',p.nome,'CAD/PRO existente inativo; vínculo não criado.')
                continue
            _, novo = CADProPropriedade.objects.get_or_create(cad_pro=cad,propriedade=p)
            resultado['criados' if novo else 'reutilizados']['vinculos_cadpro'] += 1

    estoque = next((f for f in fontes_novas if f['nome']=='ESTOQUE .xlsx'),None)
    if estoque:
        fornecedores = {texto(r.get('B')) for n,r in linhas(estoque,'FORNECEDORES') if n>=2 and texto(r.get('B'))}
        fornecedores |= {texto(r.get('I')) for n,r in linhas(estoque,'COMPRA') if n>=3 and r.get('C') and texto(r.get('I'))}
        for nome in sorted(fornecedores):
            encontrados = [p for p in ParceiroFinanceiro.objects.all() if chave(p.nome)==chave(nome)]
            if encontrados:
                resultado['reutilizados']['fornecedores'] += 1
            elif len(nome)<=160:
                salvar(ParceiroFinanceiro(nome=nome,tipo='fornecedor'))
                resultado['criados']['fornecedores'] += 1
        unidades = defaultdict(set)
        produtos = {texto(r.get('B')) for n,r in linhas(estoque,'PRODUTOS') if n>=3 and texto(r.get('B'))}
        embalagem_unidade = {'LT':'l','L':'l','LITRO':'l','LITROS':'l','KG':'kg'}
        for aba, produto_col, embalagem_col in [('COMPRA','C','F'),('RETIRADA','F','I')]:
            for n,r in linhas(estoque,aba):
                if n<3 or not r.get(produto_col):
                    continue
                nome = texto(r[produto_col])
                produtos.add(nome)
                unidade = embalagem_unidade.get(chave(r.get(embalagem_col)))
                if unidade:
                    unidades[chave(nome)].add(unidade)
        # Produtos dos faturamentos têm unidade explícita no cabeçalho.
        for f in fontes_novas:
            if f['nome']=='ESTOQUE .xlsx':
                continue
            cab = dict(linhas(f,'INSUMOS'))
            produto = texto(cab.get(1,{}).get('F' if f['nome']=='CVALE.xlsx' else 'E'))
            produtos.add(produto)
            if produto:
                unidades[chave(produto)].add('l')
        existentes = defaultdict(list)
        for p in ProdutoEstoque.objects.all():
            existentes[chave(p.nome)].append(p)
        for nome in sorted(produtos):
            if not nome:
                continue
            if existentes[chave(nome)]:
                resultado['reutilizados']['produtos'] += 1
                continue
            us = unidades[chave(nome)]
            if len(us)!=1:
                pendencia('produto',nome,'Unidade litro/kg não explícita ou conflitante; embalagem preservada no histórico.')
                continue
            salvar(ProdutoEstoque(nome=nome,categoria='insumo',unidade=next(iter(us))))
            resultado['criados']['produtos'] += 1

    for f in fontes_novas:
        registros = []
        for a in f['abas']:
            for cells in a['celulas']:
                n = int(next(iter(cells))[1:])
                valores = {c: v['valor'] for c,v in cells.items()}
                erros = [f'{c}: {v["valor"]}' for c,v in cells.items() if str(v['valor']) in {'#DIV/0!','#REF!','#VALUE!','#N/A','#NUM!','#NAME?','#NULL!'}]
                registros.append((a['resumo']['aba'],n,cells,valores,erros))
        lote = LoteImportacao(arquivo_nome=f['nome'],arquivo_tamanho=f['tamanho'],arquivo_sha256=f['sha256'],status=LoteImportacao.Status.HISTORICO,total_planilhas=len(f['abas']),total_linhas=len(registros),total_erros=sum(bool(r[4]) for r in registros),total_validas=sum(not r[4] for r in registros),criado_por=usuario,metadados={'dominio':'insumos','gera_movimentacoes':False,'gera_dividas':False,'regra_compra':'compra permanece no fornecedor; retirada é entrega à fazenda','area_alqueire_hectares':'2.42','fonte_integral_preservada':True,'pendencias_cadastro':resultado['pendencias'],'resumo_cadastros':dict(resultado['criados'])})
        salvar(lote)
        objs=[]
        for seq,(aba,n,cells,valores,erros) in enumerate(registros,1):
            prop = associacoes.get((f['nome'],n)) if aba=='INSUMOS' else None
            h = hashlib.sha256(json.dumps([f['sha256'],aba,n],ensure_ascii=False).encode()).hexdigest()
            normalizados={'natureza':'histórico de insumos','aba':aba,'linha':n,'valores_por_celula':valores,'propriedade_cadastrada':prop.nome if prop else None}
            campos={'COMPRA':{'data_compra':'B','produto':'C','cultura':'D','quantidade_embalagens':'E','embalagem':'F','conteudo_embalagem_litros_ou_kg':'G','produtor':'H','fornecedor':'I','custo_embalagem':'J','vencimento_original':'K','quantidade_litros_ou_kg':'L','custo_por_litro_ou_kg':'M','valor_total':'N'},'RETIRADA':{'documento_fiscal':'B','propriedade':'C','produtor':'D','data_entrega':'E','produto':'F','cultura':'G','quantidade_embalagens':'H','embalagem':'I','conteudo_embalagem_litros_ou_kg':'J','fornecedor':'K','quantidade_litros_ou_kg':'L'}}
            for campo,col in campos.get(aba,{}).items():
                normalizados[campo]=valores.get(col+str(n))
            objs.append(LinhaImportacao(lote_importacao=lote,sequencia=seq,planilha=aba,linha_origem=n,tipo=LinhaImportacao.Tipo.HISTORICO,status=LinhaImportacao.Status.ERRO if erros else LinhaImportacao.Status.VALIDA,hash_linha=h,dados_originais=cells,dados_normalizados=normalizados,erros=erros,advertencias=[],propriedade=prop,associacao='propriedade' if prop else 'nao_associada'))
        LinhaImportacao.objects.bulk_create(objs,batch_size=200)
        assert lote.linhas.count()==len(registros)
        resultado['lotes'].append({'id':lote.pk,'arquivo':f['nome'],'linhas':len(registros),'erros':lote.total_erros})
    assert antes == (MovimentacaoEstoque.objects.count(),LancamentoFinanceiro.objects.count()), 'Histórico não pode alterar saldos nem dívidas.'
    if not aplicar:
        transaction.set_rollback(True)
resultado['criados']=dict(resultado['criados'])
resultado['reutilizados']=dict(resultado['reutilizados'])
print(json.dumps(resultado,ensure_ascii=False,default=str))

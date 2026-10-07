from datetime import date
from decimal import Decimal
from io import BytesIO
from uuid import uuid4
import re
from openpyxl import load_workbook
from rest_framework.test import APITestCase
from .test_cargas_colhidas import CargaColhidaBase
from .models import TerceiroCadastro, PendenciaConferencia, EntradaProducaoTerceiro, MovimentoProducaoTerceiro
from .fechamentos import movimentos_periodo
from apps.accounts.models import AcessoUsuario


class AuditoriaCorrecoesTests(CargaColhidaBase,APITestCase):
    def setUp(self):
        self.criar_contexto();self.client.force_authenticate(self.usuario)
        self.dados=dict(depositante='Mesmo nome',cultura='Soja',safra='2026',armazem=self.armazem.pk,peso_bruto_kg='100',umidade_percentual='13',impureza_percentual='0',defeitos_percentual='0',data_entrada='2026-10-01')

    def entrada(self,**d):
        r=self.client.post('/api/graos/terceiros/entradas/',{**self.dados,**d},format='json',HTTP_IDEMPOTENCY_KEY=str(uuid4()))
        self.assertEqual(r.status_code,201,r.data);return r.data

    def fechar(self,cultura='Soja',**d):
        dados={**dict(armazem=self.armazem.pk,cultura=cultura,safra='2026',inicio='2026-10-01',fim='2026-10-03',justificativa='Conferência',chave_idempotencia=str(uuid4())),**d}
        r=self.client.post('/api/core/fechamentos/',dados,format='json');self.assertEqual(r.status_code,201,r.data);return r.data,dados

    def test_homonimos_separados_resumo_extrato_e_previa(self):
        a=TerceiroCadastro.objects.create(codigo='A',nome='Mesmo nome');b=TerceiroCadastro.objects.create(codigo='B',nome='Mesmo nome')
        ea=self.entrada(terceiro=a.pk);self.entrada(terceiro=b.pk)
        resumo=self.client.get('/api/graos/terceiros/resumo/').data
        self.assertEqual(len(resumo['itens']),2)
        filtro=self.client.get('/api/graos/terceiros/extrato/',{'terceiro':a.pk})
        self.assertEqual(filtro.status_code,200);self.assertEqual(filtro.data['total'],1)
        self.assertEqual(filtro.data['itens'][0]['entrada'],ea['id'])
        self.assertEqual(self.client.get('/api/graos/terceiros/extrato/',{'depositante':'Mesmo nome'}).status_code,400)
        previa=self.client.post('/api/graos/cargas-colhidas/conferencia-pesagem/previa/',{**self.dados,'origem':'terceiro','terceiro':a.pk},format='json')
        self.assertEqual(previa.data['duplicados'],[ea['id']])

    def test_recebimentos_legados_sem_uniao_automatica(self):
        a=self.entrada();self.entrada()
        self.assertEqual(len(self.client.get('/api/graos/terceiros/resumo/').data['itens']),2)
        self.assertEqual(self.client.get('/api/graos/terceiros/extrato/',{'entrada':a['id']}).data['total'],1)

    def test_fechamento_destino_exige_confirmacao_preserva_historia(self):
        e=self.entrada();p,_=self.fechar('Milho')
        d={**self.dados,'cultura':'Milho','data_entrada':'2026-10-03','versao':e['versao'],'motivo':'Corrigir classificação'}
        url=f"/api/graos/terceiros/entradas/{e['id']}/";chave=str(uuid4())
        r=self.client.patch(url,d,format='json',HTTP_IDEMPOTENCY_KEY=chave);self.assertEqual(r.status_code,409)
        r=self.client.patch(url,d,format='json',HTTP_IDEMPOTENCY_KEY=chave,HTTP_CONFIRMAR_PERIODO_FECHADO='sim');self.assertEqual(r.status_code,200,r.data)
        old=movimentos_periodo(self.armazem,'Soja','2026',date(2026,10,2))[1]
        new=movimentos_periodo(self.armazem,'Milho','2026',date(2026,10,2))[1]
        self.assertEqual(sum(v for _,_,v in old),Decimal(100));self.assertEqual(sum(v for _,_,v in new),0)
        atual=movimentos_periodo(self.armazem,'Milho','2026',date(2026,10,3))[1]
        self.assertEqual(sum(v for _,_,v in atual),Decimal(100))
        fechamento=next(x for x in self.client.get('/api/core/fechamentos/').data if x['id']==p['id'])
        self.assertEqual(fechamento['saldo_terceiros_kg'],'0.000');self.assertTrue(fechamento['alterado'])
        self.assertTrue(PendenciaConferencia.objects.filter(tipo='periodo').exists())

    def test_carga_propria_fechada_e_confirmacao(self):
        d={k:getattr(v,'pk',v) for k,v in self.dados_carga().items()};d.pop('grupo_colheita')
        d.update(propriedade=self.propriedade.pk,cad_pro=str(self.cad_pro.pk),cultura='Soja',safra='2026')
        self.fechar(inicio=str(d['data_colheita']),fim=str(d['data_colheita']))
        url='/api/graos/cargas-colhidas/'
        self.assertEqual(self.client.post(url,d,format='json').status_code,409)
        r=self.client.post(url,d,format='json',HTTP_CONFIRMAR_PERIODO_FECHADO='sim');self.assertEqual(r.status_code,201,r.data)
        self.assertEqual(self.client.delete(f"{url}{r.data['id']}/",{'motivo':'Corrigir'},format='json').status_code,409)

    def test_reenvio_confirmado_apos_fechamento(self):
        chave=str(uuid4());url='/api/graos/terceiros/entradas/'
        a=self.client.post(url,self.dados,format='json',HTTP_IDEMPOTENCY_KEY=chave);self.assertEqual(a.status_code,201)
        self.fechar()
        b=self.client.post(url,self.dados,format='json',HTTP_IDEMPOTENCY_KEY=chave);self.assertEqual(b.status_code,200)
        self.assertEqual(a.data['id'],b.data['id']);self.assertEqual(MovimentoProducaoTerceiro.objects.count(),1)
        self.assertEqual(self.client.post(url,{**self.dados,'peso_bruto_kg':'200'},format='json',HTTP_IDEMPOTENCY_KEY=chave).status_code,400)

    def test_detalhe_historico_e_versao_pendencia(self):
        p=PendenciaConferencia.objects.create(referencia='teste',tipo='peso',titulo='Conferir',responsavel=self.usuario)
        url=f'/api/core/pendencias-conferencia/{p.pk}/'
        self.assertEqual(self.client.get(url).status_code,200)
        d={'versao':1,'situacao':'resolvida','motivo':'Pesagem conferida','assumir':True}
        self.assertEqual(self.client.patch(url,d,format='json').status_code,200)
        self.assertEqual(self.client.patch(url,d,format='json').status_code,409)
        self.assertEqual(len(self.client.get(url).data['historico']),1)
        self.assertEqual(self.client.get('/api/core/pendencias-conferencia/999/').status_code,404)

    def test_contagem_divergente_cria_pendencia_sem_alterar_saldo(self):
        e=self.entrada()
        d=dict(armazem=self.armazem.pk,cultura='Soja',safra='2026',data_contagem='2026-10-07',contado_kg='90',justificativa='Balança',chave_idempotencia=str(uuid4()))
        a=self.client.post('/api/core/conferencia-estoque/',d,format='json');self.assertEqual(a.status_code,201)
        self.assertEqual(self.client.post('/api/core/conferencia-estoque/',d,format='json').status_code,200)
        self.assertEqual(PendenciaConferencia.objects.filter(tipo='estoque').count(),1)
        self.assertEqual(EntradaProducaoTerceiro.objects.get(pk=e['id']).saldo_kg,Decimal(100))

    def test_retirada_pdf_excel_com_snapshot_e_permissao(self):
        e=self.entrada();r=self.client.post(f"/api/graos/terceiros/entradas/{e['id']}/registrar-saida/",dict(quantidade_kg='10',data_movimento='2026-10-02',destino='Cliente',motorista='Motorista',placa='ABC1D23'),format='json',HTTP_IDEMPOTENCY_KEY=str(uuid4()))
        self.assertEqual(r.status_code,201,r.data);m=next(x for x in r.data['movimentos'] if x['tipo']=='saida')
        url=f"/api/graos/terceiros/movimentos/{m['id']}/"
        self.assertTrue(self.client.get(url+'pdf/').content.startswith(b'%PDF'))
        excel=self.client.get(url+'excel/');ws=load_workbook(BytesIO(excel.content)).active
        valores=[c.value for linha in ws for c in linha]
        self.assertEqual(valores.count('Cliente'),2)
        self.assertEqual(m['snapshot_depois']['depositante'],'Mesmo nome')
        AcessoUsuario.objects.create(usuario=self.usuario,modulos=['cargas'],permissoes={'cargas':['consultar']})
        self.assertEqual(self.client.get(url+'pdf/').status_code,403)

    def test_cadastro_codigo_normalizado_e_inativo(self):
        url='/api/graos/terceiros/cadastros/'
        a=self.client.post(url,{'codigo':' abc ','nome':'Mesmo nome'},format='json');self.assertEqual(a.status_code,201)
        self.assertEqual(a.data['codigo'],'ABC')
        self.assertEqual(self.client.post(url,{'codigo':'abc','nome':'Outro'},format='json').status_code,400)
        self.assertEqual(self.client.patch(f"{url}{a.data['id']}/",{'ativo':False},format='json').status_code,200)
        r=self.client.post('/api/graos/terceiros/entradas/',{**self.dados,'terceiro':a.data['id']},format='json',HTTP_IDEMPOTENCY_KEY=str(uuid4()))
        self.assertEqual(r.status_code,400)

    def test_pdf_extenso_paginado_sem_corte(self):
        e=self.entrada(observacoes='Linha de conferência\n'*1000+'FIM DAS OBSERVAÇÕES')
        r=self.client.get(f"/api/graos/terceiros/entradas/{e['id']}/pdf/")
        self.assertEqual(r.status_code,200);self.assertGreater(len(re.findall(rb'/Type /Page\b',r.content)),2)

    def test_paginacao_e_permissoes_da_fila(self):
        self.entrada()
        self.assertEqual(self.client.get('/api/graos/terceiros/entradas/',{'pagina':1}).data['total'],1)
        self.assertEqual(self.client.get('/api/graos/terceiros/entradas/',{'pagina':0}).status_code,400)
        AcessoUsuario.objects.create(usuario=self.usuario,modulos=['mercado'],permissoes={'mercado':['consultar']})
        self.assertEqual(self.client.get('/api/core/pendencias-conferencia/').status_code,403)
        self.assertEqual(self.client.get('/api/core/fechamentos/').status_code,403)

    def test_cadastro_sem_nome_na_requisicao_e_fila_restrita(self):
        t=TerceiroCadastro.objects.create(codigo='CAD',nome='Nome oficial')
        d={k:v for k,v in self.dados.items() if k!='depositante'}
        r=self.client.post('/api/graos/terceiros/entradas/',{**d,'terceiro':t.pk},format='json',HTTP_IDEMPOTENCY_KEY=str(uuid4()))
        self.assertEqual(r.status_code,201);self.assertEqual(r.data['depositante'],'Nome oficial')
        p=PendenciaConferencia.objects.create(referencia='terceiro',tipo='peso',titulo='Privado de cargas',detalhes={'origem':'terceiro'},responsavel=self.usuario)
        AcessoUsuario.objects.create(usuario=self.usuario,modulos=['producao-saldos'],permissoes={'producao-saldos':['consultar','editar']})
        self.assertEqual(self.client.get('/api/core/pendencias-conferencia/',{'situacao':''}).data,[])
        self.assertEqual(self.client.get(f'/api/core/pendencias-conferencia/{p.pk}/').status_code,403)
        self.assertEqual(self.client.patch(f'/api/core/pendencias-conferencia/{p.pk}/',{'versao':1,'situacao':'resolvida','motivo':'Teste'},format='json').status_code,403)

    def test_fechamentos_consulta_em_lote_e_reenvio(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        p,d=self.fechar()
        self.assertEqual(self.client.post('/api/core/fechamentos/',d,format='json').status_code,200)
        with CaptureQueriesContext(connection) as q:
            a=self.client.get('/api/core/fechamentos/')
        base=len(q)
        for _ in range(4):self.fechar()
        with CaptureQueriesContext(connection) as q:
            a=self.client.get('/api/core/fechamentos/')
        self.assertEqual(len(q),base)
        self.assertTrue(all(not i['alterado'] for i in a.data))


from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless
from django.db import connection, close_old_connections
from django.test import TransactionTestCase
from rest_framework.test import APIClient


@skipUnless(connection.vendor=='postgresql','Exige bloqueios reais PostgreSQL')
class AuditoriaConcorrenciaTests(CargaColhidaBase,TransactionTestCase):
    def setUp(self):self.criar_contexto()

    def paralelos(self,acoes):
        barreira=Barrier(2)
        def executar(acao):
            close_old_connections()
            try:
                c=APIClient();c.force_authenticate(self.usuario);barreira.wait(timeout=15)
                return acao(c)
            finally:close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            tarefas=[pool.submit(executar,a) for a in acoes]
            return [t.result(timeout=30) for t in tarefas]

    def test_cadastro_codigo_concorrente_sem_erro_interno(self):
        def cadastrar(c):return c.post('/api/graos/terceiros/cadastros/',{'codigo':'MESMO','nome':'Terceiro'},format='json').status_code
        self.assertEqual(sorted(self.paralelos([cadastrar,cadastrar])),[201,400])
        self.assertEqual(TerceiroCadastro.objects.count(),1)

    def test_fechamento_e_entrada_serializados(self):
        def fechar(c):return c.post('/api/core/fechamentos/',dict(armazem=self.armazem.pk,cultura='Soja',safra='2026',inicio='2026-10-01',fim='2026-10-01',justificativa='Conferência',chave_idempotencia=str(uuid4())),format='json')
        def entrada(c):return c.post('/api/graos/terceiros/entradas/',dict(depositante='Teste',cultura='Soja',safra='2026',armazem=self.armazem.pk,peso_bruto_kg='100',umidade_percentual='13',impureza_percentual='0',defeitos_percentual='0',data_entrada='2026-10-01'),format='json',HTTP_IDEMPOTENCY_KEY=str(uuid4()))
        fechamento,registro=self.paralelos([fechar,entrada])
        self.assertEqual(fechamento.status_code,201)
        self.assertIn(registro.status_code,(201,409))
        self.assertEqual(Decimal(fechamento.data['saldo_terceiros_kg']),Decimal(100) if registro.status_code==201 else Decimal(0))

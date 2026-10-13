from datetime import date
from decimal import Decimal
from uuid import uuid4
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from apps.accounts.models import AcessoUsuario
from apps.graos.test_cargas_colhidas import CargaColhidaBase
from apps.graos.cargas_services import registrar_carga_colhida
from apps.graos.services import registrar_ajuste
from apps.graos.models import PendenciaConferencia, ConferenciaEstoque
from apps.producao.models import OperacaoAgricola
from apps.talhoes.models import Talhao
from .models import ChecklistSafra, RegistroAlteracao


class RevisaoGestaoTests(CargaColhidaBase, APITestCase):
    def setUp(self):
        self.criar_contexto()
        self.client.force_authenticate(self.usuario)

    def transferencia(self):
        r = self.client.post('/api/graos/terceiros/entradas/', dict(depositante='Externo', cultura='Soja', safra='2026/2027', armazem=self.armazem.pk,
            peso_bruto_kg='100', umidade_percentual='13', impureza_percentual='0', defeitos_percentual='0', data_entrada='2026-10-01'), format='json', HTTP_IDEMPOTENCY_KEY=str(uuid4()))
        self.assertEqual(r.status_code, 201, r.data)
        entrada = r.data
        r = self.client.post(f"/api/graos/terceiros/entradas/{entrada['id']}/transferir/", dict(versao=entrada['versao'], propriedade=self.propriedade.pk,
            cad_pro=str(self.cad_pro.pk), quantidade_kg='30', data_movimento='2026-10-02', observacoes='Estoque externo identificado'), format='json', HTTP_IDEMPOTENCY_KEY=str(uuid4()))
        self.assertEqual(r.status_code, 201, r.data)
        return entrada, r.data

    def test_checklist_persiste_versao_historico_e_nao_sobrescreve(self):
        d = dict(safra='2026/2027', etapas=['saldo'], observacoes='Conferência parcial', versao=0)
        r = self.client.put('/api/core/checklist-safra/', d, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['versao'], 1)
        self.assertEqual(r.data['responsavel'], self.usuario.username)
        self.assertEqual(self.client.put('/api/core/checklist-safra/', d, format='json').status_code, 409)
        d.update(versao=1, etapas=['saldo','financeiro'])
        self.assertEqual(self.client.put('/api/core/checklist-safra/', d, format='json').data['versao'], 2)
        r = self.client.get('/api/core/checklist-safra/', {'safra':d['safra']})
        self.assertEqual(r.data['etapas'], ['saldo','financeiro'])
        self.assertEqual(len(r.data['historico']), 2)
        self.assertEqual(ChecklistSafra.objects.count(), 1)

    def test_checklist_privado_e_permissao_por_acao(self):
        self.client.put('/api/core/checklist-safra/', dict(safra='2026', etapas=[], versao=0), format='json')
        outro = get_user_model().objects.create_user('outro')
        acesso = AcessoUsuario.objects.create(usuario=outro, modulos=['relatorios'], permissoes={'relatorios':['consultar']})
        self.client.force_authenticate(outro)
        self.assertEqual(self.client.get('/api/core/checklist-safra/', {'safra':'2026'}).data['versao'], 0)
        self.assertEqual(self.client.put('/api/core/checklist-safra/',dict(safra='2026', etapas=[], versao=0),format='json').status_code,403)
        self.assertEqual(RegistroAlteracao.objects.filter(entidade='checklist_safra').count(), 1)

    def test_checklist_valida_etapas_e_safra(self):
        for d in (dict(safra='',etapas=[],versao=0), dict(safra='2026',etapas=['saldo','saldo'],versao=0), dict(safra='2026',etapas=['falso'],versao=0)):
            self.assertEqual(self.client.put('/api/core/checklist-safra/',d,format='json').status_code,400)

    def test_extrato_saldo_inicial_pagina_e_origem_externa(self):
        carga = registrar_carga_colhida(usuario=self.usuario, **self.dados_carga())
        self.transferencia()
        for n in range(27):
            registrar_ajuste(usuario=self.usuario,lote=carga.lote,delta_fisico_kg=1,chave_idempotencia=str(uuid4()),data_movimento=date(2026,10,3))
        d = dict(propriedade=self.propriedade.pk,cad_pro=str(self.cad_pro.pk),cultura='Soja',safra='2026/2027',inicio='2026-10-01',fim='2026-10-07')
        r = self.client.get('/api/core/extrato-cadpro/',d)
        self.assertEqual(r.status_code,200,r.data)
        self.assertEqual(r.data['saldo_inicial_kg'],carga.peso_liquido_kg)
        self.assertEqual(r.data['saldo_final_kg'],carga.peso_liquido_kg+57)
        self.assertTrue(r.data['resultados'][0]['origem_externa'])
        self.assertEqual(len(r.data['resultados']),25)
        r = self.client.get('/api/core/extrato-cadpro/',{**d,'pagina':2})
        self.assertEqual(len(r.data['resultados']),3)
        self.assertEqual(r.data['resultados'][-1]['saldo_kg'],r.data['saldo_final_kg'])
        self.assertEqual(r.data['total'],28)

    def test_comparacao_exclui_transferencias_e_separa_custos(self):
        registrar_carga_colhida(usuario=self.usuario, **self.dados_carga())
        d={'safra':['2026/2027','2025/2026'],'cultura':'Soja','propriedade':self.propriedade.pk}
        antes=self.client.get('/api/core/comparacao-safras/',d)
        self.assertEqual(antes.status_code,200,antes.data)
        self.transferencia()
        depois=self.client.get('/api/core/comparacao-safras/',d)
        self.assertEqual(antes.data['resultados'],depois.data['resultados'])
        talhao=Talhao.objects.create(propriedade=self.propriedade,nome='Operação',area_hectares=10,cultura_atual='Soja',safra='2026/2027')
        OperacaoAgricola.objects.create(talhao=talhao,tipo='plantio',descricao='Plantio',data_planejada=date(2026,1,1),area_hectares=10,custo_realizado=900,criado_por=self.usuario)
        OperacaoAgricola.objects.create(talhao=talhao,tipo='outra',descricao='Cancelada',data_planejada=date(2026,1,1),area_hectares=10,custo_realizado=500,status='cancelada',criado_por=self.usuario)
        r=self.client.get('/api/core/comparacao-safras/',d)
        self.assertEqual(r.data['resultados'][0]['custo_operacoes'],Decimal('900'))
        self.assertEqual(r.data['resultados'][1]['quantidade_kg'],'0.000')

    def test_documentos_mostram_cancelamento_e_estorno(self):
        entrada, transferida=self.transferencia()
        r=self.client.get('/api/core/documentos/',{'tipo':'transferencia'})
        self.assertEqual(r.data['resultados'][0]['doc_situacao'],'Ativo')
        # O movimento de transferência é identificado pelo tipo, sem supor ordem.
        movimento=next(m for m in transferida['movimentos'] if m['tipo']=='transferencia')
        r=self.client.post(f"/api/graos/terceiros/movimentos/{movimento['id']}/estornar/",dict(motivo='Conferência',data_movimento='2026-10-03'),format='json',HTTP_IDEMPOTENCY_KEY=str(uuid4()))
        self.assertEqual(r.status_code,201,r.data)
        self.assertEqual(self.client.get('/api/core/documentos/',{'tipo':'transferencia'}).data['resultados'][0]['doc_situacao'],'Estornado')
        r=self.client.get('/api/core/extrato-cadpro/',dict(propriedade=self.propriedade.pk,inicio='2026-10-01',fim='2026-10-07'))
        self.assertEqual(r.data['saldo_final_kg'],0)
        self.assertTrue(all(m['origem_externa'] for m in r.data['resultados']))

    def test_origem_pendencia_usa_identificador_exato_e_respeita_acesso(self):
        entrada,_=self.transferencia()
        p=PendenciaConferencia.objects.create(referencia='teste',tipo='peso',titulo='Revisar',detalhes={'origem':'terceiro','registro':entrada['id']},responsavel=self.usuario)
        r=self.client.get(f'/api/core/pendencias-conferencia/{p.pk}/origem/')
        self.assertEqual(r.status_code,200,r.data)
        self.assertEqual(r.data['numero'],entrada['id'])
        self.assertEqual(r.data['campos']['depositante'],'Externo')
        AcessoUsuario.objects.create(usuario=self.usuario,modulos=['producao-saldos'],permissoes={'producao-saldos':['consultar']})
        self.assertEqual(self.client.get(f'/api/core/pendencias-conferencia/{p.pk}/origem/').status_code,403)

    def test_origem_contagem_imutavel(self):
        c=ConferenciaEstoque.objects.create(armazem=self.armazem,cultura='Soja',safra='2026',data_contagem=date(2026,10,1),contado_kg=100,saldo_proprio_kg=50,saldo_terceiros_kg=25,justificativa='Conferir',chave_idempotencia=uuid4(),criado_por=self.usuario)
        p=PendenciaConferencia.objects.create(referencia='contagem',tipo='estoque',titulo='Revisar',detalhes={'contagem':c.pk},responsavel=self.usuario)
        r=self.client.get(f'/api/core/pendencias-conferencia/{p.pk}/origem/')
        self.assertEqual(r.status_code,200,r.data)
        self.assertEqual(r.data['campos']['diferenca_kg'],'25.000')

    def test_financeiro_consulta_todos_titulos_sem_liquidar(self):
        from apps.financeiro.models import LancamentoFinanceiro
        titulo=LancamentoFinanceiro.objects.create(tipo='pagar',descricao='Boleto com comprovante',valor=100,status='pendente',data_vencimento=date(2026,10,7))
        self.assertEqual(self.client.get('/api/core/conferencia-financeira/').data['total'],0)
        r=self.client.get('/api/core/conferencia-financeira/',{'somente_diferencas':'false'})
        self.assertEqual(r.status_code,200,r.data)
        self.assertEqual(r.data['resultados'][0]['id'],titulo.pk)
        self.assertEqual(r.data['resultados'][0]['status'],'pendente')
        self.assertEqual(r.data['resumo']['a_menor'],0)
        titulo.refresh_from_db()
        self.assertEqual(titulo.status,'pendente')

    def test_comparacao_sem_permissao_custo_e_validacao(self):
        AcessoUsuario.objects.create(usuario=self.usuario,modulos=['relatorios'],permissoes={'relatorios':['consultar']})
        r=self.client.get('/api/core/comparacao-safras/',{'safra':['2026','2025'],'cultura':'Soja'})
        self.assertEqual(r.status_code,200,r.data)
        self.assertFalse(r.data['custo_autorizado'])
        self.assertTrue(all(l['custo_operacoes'] is None for l in r.data['resultados']))
        self.assertEqual(self.client.get('/api/core/comparacao-safras/',{'safra':['2026','2026'],'cultura':'Soja'}).status_code,400)
        self.assertEqual(self.client.get('/api/core/extrato-cadpro/',dict(propriedade=self.propriedade.pk,inicio='2026-10-07',fim='2026-10-01')).status_code,403)

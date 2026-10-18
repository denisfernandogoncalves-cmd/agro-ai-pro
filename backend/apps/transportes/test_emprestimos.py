from datetime import date
from decimal import Decimal
from uuid import uuid4
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from .models import Motorista, Caminhao, RemuneracaoMotorista, EmprestimoMotorista, PagamentoEmprestimo


class EmprestimosTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='teste-emprestimos', is_staff=True)
        self.client = APIClient(); self.client.force_authenticate(self.user)
        self.motorista = Motorista.objects.create(nome='Motorista exato')
        self.base = '/api/transportes/emprestimos/'
        self.dados = dict(motorista=self.motorista.id, data='2026-01-01', vencimento='2026-12-01', valor='1000.00', juros_percentual='10', motivo='Condições acordadas', chave=str(uuid4()))

    def criar(self):
        r = self.client.post(self.base, self.dados)
        self.assertEqual(r.status_code, 201, r.data)
        return r.data

    def pagar(self, emprestimo, valor='100', **kwargs):
        return self.client.post(f'{self.base}{emprestimo}/pagamentos/', dict(data='2026-01-20', valor=valor, observacao='Comprovante de teste isolado', chave=str(uuid4()), **kwargs))

    def test_juros_saldo_historico_e_estorno(self):
        e = self.criar(); self.assertEqual(Decimal(e['total']), Decimal('1100'))
        r = self.pagar(e['id']); self.assertEqual(r.status_code, 201, r.data)
        r2 = self.client.get(f"{self.base}{e['id']}/"); self.assertEqual(Decimal(r2.data['saldo']), 1000)
        url = f"{self.base}{e['id']}/estornar/"
        self.assertEqual(self.client.post(url, {'pagamento':r.data['id'],'motivo':'Correção justificada'}).status_code,200)
        self.assertEqual(self.client.post(url, {'pagamento':r.data['id'],'motivo':'Reenvio'}).status_code,200)
        e2 = self.client.get(f"{self.base}{e['id']}/").data
        self.assertEqual(Decimal(e2['saldo']),1100); self.assertEqual(len(e2['pagamentos']),1)
        self.assertEqual(e2['pagamentos'][0]['motivo_estorno'],'Correção justificada')

    def test_idempotencia_criacao_e_conflito(self):
        e=self.criar()
        self.assertEqual(self.client.post(self.base,self.dados).data['id'],e['id'])
        self.assertEqual(self.client.post(self.base,{**self.dados,'valor':'900'}).status_code,409)
        self.assertEqual(EmprestimoMotorista.objects.count(),1)

    def test_idempotencia_pagamento(self):
        e=self.criar(); dados=dict(data='2026-01-20',valor='20',observacao='Pix',chave=str(uuid4()))
        url=f"{self.base}{e['id']}/pagamentos/"
        self.assertEqual(self.client.post(url,dados).status_code,201)
        self.assertEqual(self.client.post(url,dados).status_code,200)
        self.assertEqual(self.client.post(url,{**dados,'valor':'30'}).status_code,409)
        self.assertEqual(PagamentoEmprestimo.objects.count(),1)

    def test_saldo_datas_e_valores_invalidos(self):
        e=self.criar()
        self.assertEqual(self.pagar(e['id'],'1100.01').status_code,400)
        self.assertEqual(self.pagar(e['id'],'0').status_code,400)
        url=f"{self.base}{e['id']}/pagamentos/"
        self.assertEqual(self.client.post(url,dict(data='2025-12-31',valor='1',observacao='teste',chave=str(uuid4()))).status_code,400)
        self.assertEqual(self.client.post(self.base,{**self.dados,'chave':str(uuid4()),'vencimento':'2025-01-01'}).status_code,400)

    def remuneracao(self, placa='ABC1D23', nome=None):
        c=Caminhao.objects.create(placa=placa,veiculo='Teste')
        return RemuneracaoMotorista.objects.create(caminhao=c,motorista=nome or self.motorista.nome,competencia=date(2026,1,1),salario=Decimal('1000'))

    def test_holerite_nao_duplica_placas_e_externo(self):
        e=self.criar(); r=self.remuneracao(); self.remuneracao('DEF2E34')
        self.assertEqual(self.pagar(e['id'],'100',remuneracao=r.id).status_code,201)
        self.assertEqual(self.pagar(e['id'],'50').status_code,201)
        h=self.client.get('/api/transportes/remuneracoes/imprimir/?mes=2026-01').data[0]
        self.assertEqual(Decimal(h['total']),2000)
        self.assertEqual(Decimal(h['total_liquido']),1900)
        self.assertEqual(Decimal(h['desconto_emprestimos']),100)
        self.assertEqual(len(h['emprestimos_pagos']),1)
        r.conta_pagar.refresh_from_db(); self.assertEqual(r.conta_pagar.valor,900)
        p=PagamentoEmprestimo.objects.get(remuneracao=r)
        self.assertEqual(self.client.post(f"{self.base}{e['id']}/estornar/",{'pagamento':p.id,'motivo':'Correção'}).status_code,200)
        r.conta_pagar.refresh_from_db(); self.assertEqual(r.conta_pagar.valor,1000)

    def test_desconto_total_e_estorno_reabre_titulo_zerado(self):
        e=self.criar(); r=self.remuneracao()
        p=self.pagar(e['id'],'1000',remuneracao=r.id)
        self.assertEqual(p.status_code,201,p.data)
        r.conta_pagar.refresh_from_db(); self.assertEqual(r.conta_pagar.status,'cancelado')
        resposta=self.client.post(f"{self.base}{e['id']}/estornar/",{'pagamento':p.data['id'],'motivo':'Erro no desconto'})
        self.assertEqual(resposta.status_code,200,resposta.data)
        r.conta_pagar.refresh_from_db();self.assertEqual(r.conta_pagar.status,'pendente');self.assertEqual(r.conta_pagar.valor,1000)

    def test_nome_aproximado_nao_vincula(self):
        e=self.criar(); r=self.remuneracao(nome='MOTORISTA EXATO')
        self.assertEqual(self.pagar(e['id'],remuneracao=r.id).status_code,400)

    def test_registros_inalteraveis_e_permissoes(self):
        e=self.criar()
        self.assertEqual(self.client.patch(f"{self.base}{e['id']}/",{'valor':'1'}).status_code,405)
        self.assertEqual(self.client.delete(f"{self.base}{e['id']}/").status_code,405)
        self.client.force_authenticate(None)
        self.assertIn(self.client.get(self.base).status_code,(401,403))

    def test_sem_juros(self):
        self.dados['juros_percentual']='0';e=self.criar();self.assertEqual(Decimal(e['total']),1000)

    def test_competencia_e_remuneracao_liquidada_protegidas(self):
        e=self.criar();r=self.remuneracao()
        url=f"{self.base}{e['id']}/pagamentos/"
        dados=dict(data='2026-02-01',valor='100',observacao='Teste',remuneracao=r.pk,chave=str(uuid4()))
        self.assertEqual(self.client.post(url,dados).status_code,400)
        from apps.financeiro.services import liquidar_lancamento
        liquidar_lancamento(r.conta_pagar,data_liquidacao=date(2026,1,20),valor_liquidado=Decimal('1000'))
        self.assertEqual(self.pagar(e['id'],remuneracao=r.id).status_code,400)
        self.assertEqual(PagamentoEmprestimo.objects.count(),0)

    def test_correcao_remuneracao_preserva_historico(self):
        e=self.criar();r=self.remuneracao();self.assertEqual(self.pagar(e['id'],remuneracao=r.pk).status_code,201)
        from rest_framework.exceptions import ValidationError
        r.motorista='Outro'
        with self.assertRaises(ValidationError): r.save()
        r.refresh_from_db();r.salario=Decimal('50')
        with self.assertRaises(ValidationError): r.save()

    def test_acesso_restrito(self):
        from apps.accounts.models import AcessoUsuario
        user=get_user_model().objects.create_user(username='consulta-emprestimos')
        AcessoUsuario.objects.create(usuario=user,modulos=['transportes'],permissoes={'transportes':['consultar']})
        self.client.force_authenticate(user)
        self.assertEqual(self.client.get(self.base).status_code,200)
        self.assertEqual(self.client.post(self.base,self.dados).status_code,403)
        self.assertEqual(self.client.get('/api/financeiro/prestacoes/').status_code,403)


from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from django.db import close_old_connections, connection
from django.test import TransactionTestCase
from unittest import skipUnless


@skipUnless(connection.vendor == 'postgresql', 'Exige bloqueios reais PostgreSQL')
class ConcorrenciaEmprestimosTests(TransactionTestCase):
    def test_pagamentos_simultaneos_nao_ultrapassam_saldo(self):
        user=get_user_model().objects.create_user(username='concorrencia-emprestimos',is_staff=True)
        motorista=Motorista.objects.create(nome='Motorista concorrência')
        e=EmprestimoMotorista.objects.create(motorista=motorista,nome_original=motorista.nome,data=date(2026,1,1),vencimento=date(2026,12,1),valor=Decimal('1000'),motivo='Teste isolado',chave=uuid4(),usuario=user)
        barreira=Barrier(2)
        def pagar(_):
            close_old_connections()
            try:
                client=APIClient();client.force_authenticate(user)
                barreira.wait(timeout=15)
                return client.post(f'/api/transportes/emprestimos/{e.id}/pagamentos/',dict(data='2026-01-20',valor='700',observacao='Simultâneo',chave=str(uuid4()))).status_code
            finally: close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            resultados=list(pool.map(pagar,range(2)))
        self.assertEqual(sorted(resultados),[201,400])
        self.assertEqual(e.pagamentos.count(),1)

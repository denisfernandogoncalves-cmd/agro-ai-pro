from decimal import Decimal
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from apps.accounts.models import AcessoUsuario
from apps.graos.models import PosicaoSaldoGraos, MovimentacaoGraos
from apps.graos.tests import GraosSaldoBase
from .models import RascunhoFormulario

class ConferenciaTests(GraosSaldoBase, APITestCase):
    def setUp(self):
        self.criar_contexto()
        self.usuario.is_staff=True;self.usuario.save()
        self.client.force_authenticate(self.usuario)
        self.creditar("100")
        self.posicao=PosicaoSaldoGraos.objects.get(cad_pro=self.cad_pro)
    def test_conferencia_completa_paginada_baseline_e_nao_altera_saldo(self):
        for i in range(26):self.creditar("1",f"paginacao-{i}")
        r=self.client.get(f"/api/core/conferencia/{self.posicao.pk}/?pagina=2")
        self.assertEqual(r.status_code,200,r.data)
        self.assertEqual(r.data["total_movimentos"],27)
        self.assertEqual(Decimal(r.data["itens"][0]["saldo_acumulado_kg"]),Decimal("125"))
        self.assertEqual(Decimal(r.data["totais"]["fisico"]),Decimal("126"))
        self.assertEqual(Decimal(r.data["diferenca_fisico_kg"]),0)
        self.posicao.refresh_from_db();self.assertEqual(self.posicao.saldo_fisico_kg,Decimal("126"))
    def test_conferencia_divergente_aponta_sem_reconciliar(self):
        PosicaoSaldoGraos.objects.filter(pk=self.posicao.pk).update(saldo_fisico_kg=Decimal("110"))
        r=self.client.get(f"/api/core/conferencia/{self.posicao.pk}/")
        self.assertEqual(Decimal(r.data["diferenca_fisico_kg"]),10)
        self.posicao.refresh_from_db();self.assertEqual(self.posicao.saldo_fisico_kg,110)
    def test_simular_saida_rascunho_negativo_sem_gravar(self):
        quantidade=MovimentacaoGraos.objects.count()
        for tipo,esperado in [("saida","-50"),("rascunho","100")]:
            r=self.client.post("/api/core/simular-venda/",{"posicao":self.posicao.pk,"quantidade_kg":"150","tipo":tipo},format="json")
            self.assertEqual(r.status_code,200,r.data)
            self.assertEqual(Decimal(r.data["saldo_posterior_kg"]),Decimal(esperado))
        self.assertEqual(MovimentacaoGraos.objects.count(),quantidade)
        self.posicao.refresh_from_db();self.assertEqual(self.posicao.saldo_fisico_kg,100)
    def test_simular_origem_nova_nao_cria_posicao(self):
        count=PosicaoSaldoGraos.objects.count()
        r=self.client.post("/api/core/simular-venda/",{"nova_posicao":{"propriedade":self.propriedade.pk,"cad_pro":str(self.cad_pro.pk),"armazem":self.armazem.pk,"cultura":"Milho","safra":"2027","classificacao_codigo":"PADRAO"},"quantidade_kg":"10","tipo":"saida"},format="json")
        self.assertEqual(r.status_code,200,r.data);self.assertEqual(r.data["saldo_posterior_kg"],"-10.000")
        self.assertEqual(PosicaoSaldoGraos.objects.count(),count)
    def test_estorno_motivo_original_preservado_idempotente(self):
        m=MovimentacaoGraos.objects.get(posicao=self.posicao)
        url=f"/api/core/conferencia/movimentos/{m.pk}/estornar/"
        self.assertEqual(self.client.post(url,{"chave_idempotencia":"estorno"},format="json").status_code,400)
        for esperado in (201,200):
            r=self.client.post(url,{"chave_idempotencia":"estorno","observacoes":"Correção de teste"},format="json")
            self.assertEqual(r.status_code,esperado,r.data)
        self.assertTrue(MovimentacaoGraos.objects.filter(pk=m.pk).exists())
        self.assertEqual(MovimentacaoGraos.objects.filter(estorno_de=m).count(),1)
        self.posicao.refresh_from_db();self.assertEqual(self.posicao.saldo_fisico_kg,0)
    def test_restricoes_por_acao_e_setor(self):
        u=get_user_model().objects.create_user("somente-consulta")
        AcessoUsuario.objects.create(usuario=u,modulos=["vendas"],permissoes={"vendas":["consultar"]})
        self.client.force_authenticate(u)
        self.assertEqual(self.client.get(f"/api/core/conferencia/{self.posicao.pk}/").status_code,403)
        self.assertEqual(self.client.post("/api/core/simular-venda/",{"posicao":self.posicao.pk,"quantidade_kg":"10","tipo":"saida"},format="json").status_code,200)
        self.assertEqual(self.client.put("/api/core/rascunhos/vendas/",{"dados":{}},format="json").status_code,403)
        self.assertEqual(self.client.post("/api/core/conferencia/movimentos/1/estornar/",{},format="json").status_code,403)
    def test_rascunhos_privados_e_whitelist(self):
        url="/api/core/rascunhos/vendas/"
        dados={"formulario":{"quantidade_kg":"50","cliente_nome":"Particular"},"novaSaida":{"nota_produtor":"123","peso_bruto_kg":"100","tara_kg":"50","umidade_percentual":"20","avariados_percentual":"3","quebrados_percentual":"4","ph":"72"}}
        self.assertEqual(self.client.put(url,{"dados":dados},format="json").status_code,200)
        u=get_user_model().objects.create_user("outra-conta",is_staff=True);self.client.force_authenticate(u)
        self.assertIsNone(self.client.get(url).data["dados"])
        self.assertEqual(self.client.delete(url).status_code,204)
        self.assertEqual(RascunhoFormulario.objects.count(),1)
        self.assertEqual(self.client.put(url,{"dados":{"senha":"secreto"}},format="json").status_code,400)
        self.client.force_authenticate(self.usuario)
        self.assertEqual(self.client.get(url).data["dados"],dados)
        self.assertEqual(self.client.delete(url).status_code,204)
        self.assertEqual(RascunhoFormulario.objects.count(),0)
    def test_relatorio_salvo_valida_colunas_impressao(self):
        dados={"contexto":"relatorios","nome":"Relatório completo","filtros":{"secao":"producao_propriedade"},"configuracao":{"colunas":["propriedade","kg"],"orientacao":"retrato","densidade":"compacta"}}
        r=self.client.post("/api/core/favoritos/",dados,format="json")
        self.assertEqual(r.status_code,201,r.data);self.assertEqual(r.data["configuracao"],dados["configuracao"])
        dados["nome"]="Inválido";dados["configuracao"]["colunas"]=["senha"]
        self.assertEqual(self.client.post("/api/core/favoritos/",dados,format="json").status_code,400)
    def test_parametros_invalidos(self):
        self.assertEqual(self.client.get(f"/api/core/conferencia/{self.posicao.pk}/?pagina=0").status_code,400)
        self.assertEqual(self.client.post("/api/core/simular-venda/",{"posicao":self.posicao.pk,"quantidade_kg":"-1","tipo":"saida"},format="json").status_code,400)

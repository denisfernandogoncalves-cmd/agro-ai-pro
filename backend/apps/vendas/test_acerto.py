from decimal import Decimal
from django.utils import timezone
from rest_framework.test import APITestCase
from apps.cadpro.models import CADPro
from apps.financeiro.models import LancamentoFinanceiro
from .tests import ContextoVendaMixin
from .models import ContratoComercial,VinculoAcerto

class AcertoTests(ContextoVendaMixin,APITestCase):
    def setUp(self):
        self.criar_contexto();self.usuario.is_staff=True;self.usuario.save();self.client.force_authenticate(self.usuario)
        self.contrato=ContratoComercial.objects.create(numero="ACERTO",empresa="Comprador",produto="Soja",quantidade_kg="1000")
        self.financeiro=LancamentoFinanceiro.objects.create(tipo="receber",descricao="Recebimento",valor="100",valor_liquidado="60",status="liquidado",data_vencimento=timezone.localdate())
        self.dados={"contrato":self.contrato.pk,"cad_pro":str(self.cadpro.pk),"lancamento":self.financeiro.pk,"valor_vinculado":"80","natureza":"receita","justificativa":"Identidade conferida"}
    def consultar(self):
        return self.client.get("/api/comercial/acertos/",{"contrato":self.contrato.pk})
    def test_vinculo_reenvio_e_realizado_proporcional(self):
        for expected in (201,200):self.assertEqual(self.client.post("/api/comercial/acertos/",self.dados,format="json").status_code,expected)
        self.assertEqual(VinculoAcerto.objects.count(),1)
        r=self.consultar();self.assertEqual(r.status_code,200,r.data)
        self.assertEqual(Decimal(r.data["resumo"]["recebido"]),Decimal("48"))
        self.financeiro.refresh_from_db();self.assertEqual(self.financeiro.valor_liquidado,Decimal("60"))
    def test_orcamento_global_e_natureza(self):
        self.client.post("/api/comercial/acertos/",self.dados,format="json")
        cad=CADPro.objects.create(codigo="OUTRO",descricao="Outro titular")
        for extra in ({"cad_pro":str(cad.pk),"valor_vinculado":"30"},{"natureza":"frete"},{"valor_vinculado":"NaN"}):
            r=self.client.post("/api/comercial/acertos/",{**self.dados,**extra},format="json");self.assertEqual(r.status_code,400,r.data)
    def test_desvincular_preserva_financeiro_e_versao(self):
        r=self.client.post("/api/comercial/acertos/",self.dados,format="json");url=f"/api/comercial/acertos/{r.data['id']}/"
        d={"ativo":False,"versao":1,"justificativa":"Vínculo corrigido"}
        self.assertEqual(self.client.patch(url,d,format="json").status_code,200)
        self.assertEqual(self.client.patch(url,d,format="json").status_code,409)
        self.assertEqual(Decimal(self.consultar().data["resumo"]["recebido"]),Decimal("0"))
        self.financeiro.refresh_from_db();self.assertEqual(self.financeiro.status,"liquidado")
        self.assertTrue(VinculoAcerto.objects.exists())
    def test_cancelado_e_valor_liquidado_ausente_nao_inventa_caixa(self):
        self.client.post("/api/comercial/acertos/",self.dados,format="json")
        self.financeiro.valor_liquidado=None;self.financeiro.save(update_fields=["valor_liquidado"])
        r=self.consultar();self.assertEqual(r.data["resumo"]["liquidacoes_sem_valor"],1)
        self.assertEqual(Decimal(r.data["resumo"]["recebido"]),Decimal("0"))
        self.financeiro.status="cancelado";self.financeiro.save(update_fields=["status"])
        self.assertEqual(Decimal(self.consultar().data["resumo"]["receitas_previstas"]),Decimal("0"))
    def test_edicao_financeira_inconsistente_nao_duplica_caixa(self):
        self.client.post("/api/comercial/acertos/",self.dados,format="json")
        self.financeiro.valor="50";self.financeiro.save(update_fields=["valor"])
        r=self.consultar();self.assertTrue(r.data["results"][0]["distribuicao_inconsistente"])
        self.assertIsNone(r.data["results"][0]["realizado_proporcional"])
    def test_autenticacao_e_filtros(self):
        self.assertEqual(self.client.get("/api/comercial/acertos/",{"contrato":self.contrato.pk,"cad_pro":"incorreto"}).status_code,400)
        self.client.force_authenticate(None);self.assertEqual(self.consultar().status_code,401)

    def test_permissao_financeira_obrigatoria(self):
        from apps.accounts.models import AcessoUsuario
        self.usuario.is_staff=False;self.usuario.save()
        AcessoUsuario.objects.update_or_create(usuario=self.usuario,defaults={"modulos":["vendas"],"permissoes":{"vendas":["consultar","cadastrar","editar"]}})
        self.assertEqual(self.consultar().status_code,403)
        self.assertEqual(self.client.post("/api/comercial/acertos/",self.dados,format="json").status_code,403)

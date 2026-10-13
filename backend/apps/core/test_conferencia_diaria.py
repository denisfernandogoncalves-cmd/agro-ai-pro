from decimal import Decimal
from django.utils import timezone
from rest_framework.test import APITestCase
from apps.graos.models import ConferenciaEstoque,MovimentacaoGraos
from apps.accounts.models import AcessoUsuario
from apps.vendas.tests import ContextoVendaMixin
import uuid

class ConferenciaDiariaTests(ContextoVendaMixin,APITestCase):
    def setUp(self):
        self.criar_contexto();self.usuario.is_staff=True;self.usuario.save();self.client.force_authenticate(self.usuario)
        self.filtros={"armazem":self.armazem.pk,"cultura":"Soja","safra":"2026/2027","data":timezone.localdate().isoformat()}
    def test_saldo_do_dia_sem_mutacao(self):
        before=MovimentacaoGraos.objects.count()
        r=self.client.get("/api/core/conferencia-diaria/",self.filtros)
        self.assertEqual(r.status_code,200,r.data)
        self.assertEqual(Decimal(r.data["saldo_final_fisico_kg"]),Decimal("1000"))
        self.assertEqual(Decimal(r.data["movimento_proprio_kg"]),Decimal("1000"))
        self.assertEqual(Decimal(r.data["saldo_final_terceiros_kg"]),Decimal("0"))
        self.assertEqual(MovimentacaoGraos.objects.count(),before)
    def test_contagens_paginadas_com_variacao_na_fronteira(self):
        for i in range(26):
            ConferenciaEstoque.objects.create(armazem=self.armazem,cultura="Soja",safra="2026/2027",data_contagem=timezone.localdate(),contado_kg=1000+i,saldo_proprio_kg=1000,saldo_terceiros_kg=0,justificativa="Contagem",chave_idempotencia=uuid.uuid4(),criado_por=self.usuario)
        r=self.client.get("/api/core/conferencia-diaria/",self.filtros)
        self.assertEqual(r.data["contagens_total"],26)
        self.assertEqual(len(r.data["contagens"]),25)
        self.assertEqual(Decimal(r.data["contagens"][0]["variacao_diferenca_kg"]),Decimal("1"))
        second=self.client.get("/api/core/conferencia-diaria/",{**self.filtros,"pagina_contagens":2})
        self.assertEqual(len(second.data["contagens"]),1)
        self.assertIsNone(second.data["contagens"][0]["variacao_diferenca_kg"])
        self.posicao.refresh_from_db();self.assertEqual(self.posicao.saldo_fisico_kg,Decimal("1000"))
    def test_filtros_e_permissoes(self):
        self.assertEqual(self.client.get("/api/core/conferencia-diaria/",{**self.filtros,"pagina_contagens":0}).status_code,400)
        self.usuario.is_staff=False;self.usuario.save()
        AcessoUsuario.objects.update_or_create(usuario=self.usuario,defaults={"modulos":["relatorios"],"permissoes":{"relatorios":["consultar"]}})
        self.assertEqual(self.client.get("/api/core/conferencia-diaria/",self.filtros).status_code,403)

from unittest.mock import patch
from decimal import Decimal
from rest_framework.test import APITestCase
from apps.graos.models import MovimentacaoGraos
from .tests import ContextoVendaMixin
from .services import confirmar_venda, registrar_entrega_venda
from .models import ConferenciaComprador

class ConferenciaCompradorTests(ContextoVendaMixin,APITestCase):
    def setUp(self):
        self.criar_contexto();self.usuario.is_staff=True;self.usuario.save()
        self.client.force_authenticate(self.usuario)
        self.venda=self.rascunho()
        confirmar_venda(usuario=self.usuario,venda=self.venda,chave_idempotencia="confirmar-comprador")
        self.entrega=registrar_entrega_venda(usuario=self.usuario,venda=self.venda,quantidade_kg="200",chave_idempotencia="entrega-comprador")
        self.url=f"/api/comercial/vendas/{self.venda.pk}/entregas/{self.entrega.pk}/conferencia-comprador/"
        self.dados={"versao":0,"peso_recebido_liquido_kg":"190","frete_realizado":"50","qualidade":{"umidade":"12"},"justificativa":"Ticket conferido"}
    def test_diferenca_sem_ajuste_e_versao(self):
        before=MovimentacaoGraos.objects.count()
        r=self.client.put(self.url,self.dados,format="json")
        self.assertEqual(r.status_code,200,r.data)
        self.assertEqual(Decimal(r.data["diferenca_kg"]),Decimal("-10"))
        self.assertEqual(r.data["qualidade"]["umidade"],"12.000")
        self.assertEqual(MovimentacaoGraos.objects.count(),before)
        self.assertEqual(self.client.put(self.url,self.dados,format="json").status_code,409)
        self.venda.refresh_from_db();self.assertEqual(self.venda.quantidade_entregue_kg,Decimal("200"))
    def test_limites_peso_percentual_frete(self):
        for extra in ({"peso_recebido_liquido_kg":"0"},{"qualidade":{"umidade":"101"}},{"frete_realizado":"-1"}):
            self.assertEqual(self.client.put(self.url,{**self.dados,**extra},format="json").status_code,400)
        self.assertFalse(ConferenciaComprador.objects.exists())
    def test_periodo_fechado_bloqueia_conferencia(self):
        with patch("apps.vendas.conferencia_comprador.periodos_afetados",return_value=[object()]):
            self.assertEqual(self.client.put(self.url,self.dados,format="json").status_code,409)
        self.assertFalse(ConferenciaComprador.objects.exists())
    def test_cancelamento_consulta_e_autenticacao(self):
        from django.utils import timezone
        self.entrega.cancelado_em=timezone.now();self.entrega.save(update_fields=["cancelado_em"])
        self.assertEqual(self.client.put(self.url,self.dados,format="json").status_code,409)
        self.assertTrue(self.client.get(self.url).data["cancelada"])
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(self.url).status_code,401)
    def test_anexos_vinculados_a_entrega_exata(self):
        r=self.client.get(f"/api/core/anexos/entrega/{self.entrega.pk}/")
        self.assertEqual(r.status_code,200,r.data)
        self.assertEqual(r.data,[])
        self.assertEqual(self.client.get(f"/api/core/anexos/entrega/{self.entrega.pk+10000}/").status_code,404)

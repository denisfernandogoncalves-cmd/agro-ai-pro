from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from django.utils import timezone
from unittest.mock import patch
from datetime import date
from .models import LancamentoFinanceiro
from .serializers import LancamentoFinanceiroSerializer
class AuditoriaFinanceiroTests(APITestCase):
    def setUp(self):
        self.user=get_user_model().objects.create_user("auditoria-incremento",password="x",is_staff=True)
        self.client.force_authenticate(self.user)
        self.item=LancamentoFinanceiro.objects.create(tipo="pagar",descricao="Teste",valor="100",data_vencimento=timezone.localdate())
        self.url=f"/api/financeiro/lancamentos/{self.item.pk}/"
    def test_edicao_antiga_nao_sobrescreve(self):
        versao=self.item.atualizado_em.isoformat()
        self.assertEqual(self.client.patch(self.url,{"descricao":"Atual","atualizado_em_original":versao},format="json").status_code,200)
        self.assertEqual(self.client.patch(self.url,{"descricao":"Antigo","atualizado_em_original":versao},format="json").status_code,409)
        self.item.refresh_from_db();self.assertEqual(self.item.descricao,"Atual")
    def test_liquidacao_invalida_preserva_pendente(self):
        for valor in ["NaN","Infinity","-1","0.001"]:
            r=self.client.post(self.url+"liquidar/",{"data_liquidacao":timezone.localdate().isoformat(),"valor_liquidado":valor},format="json")
            self.assertEqual(r.status_code,400)
        self.item.refresh_from_db();self.assertEqual(self.item.status,"pendente")
    def test_ano_bissexto(self):
        with patch("apps.financeiro.serializers.timezone.localdate",return_value=date(2028,2,29)):
            self.assertEqual(LancamentoFinanceiroSerializer().validate_data_vencimento(date(2028,2,29)),date(2028,2,29))

    def test_data_original_invalida_nao_altera(self):
        r=self.client.patch(self.url,{"descricao":"Inválido","atualizado_em_original":"2026-02-31T00:00:00"},format="json")
        self.assertEqual(r.status_code,400)
        self.item.refresh_from_db()
        self.assertEqual(self.item.descricao,"Teste")

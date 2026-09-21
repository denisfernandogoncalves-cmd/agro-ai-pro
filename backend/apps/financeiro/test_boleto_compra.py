import uuid
from decimal import Decimal
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from .models import LancamentoFinanceiro


class BoletoCompraTests(APITestCase):
    def setUp(self):
        self.client.force_authenticate(get_user_model().objects.create_user(username="boleto-compra"))
        self.url = "/api/financeiro/lancamentos/registrar-boleto/"
        self.dados = {
            "idempotency_key": str(uuid.uuid4()), "tipo": "pagar", "descricao": "Compra teste",
            "recebedor_nome": "Recebedor teste", "valor": "123.45", "parcela_numero": 1, "total_boletos": 4,
            "data_emissao": "2026-09-12", "data_vencimento": "2026-10-02",
            "codigo_barras": "00197100000000123451234567890123456789012345",
        }

    def test_registra_um_de_quatro_sem_dividir_ou_gerar_outros(self):
        resposta = self.client.post(self.url, self.dados, format="json")
        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.assertEqual(LancamentoFinanceiro.objects.count(), 1)
        boleto = LancamentoFinanceiro.objects.get()
        self.assertEqual(boleto.valor, Decimal("123.45"))
        self.assertEqual(str(boleto.data_vencimento), "2026-10-02")
        self.assertEqual((boleto.parcela_numero, boleto.total_boletos), (1, 4))
        self.assertEqual(boleto.codigo_barras, self.dados["codigo_barras"])
        self.assertEqual(self.client.post(self.url, self.dados, format="json").status_code, 200)
        self.assertEqual(LancamentoFinanceiro.objects.count(), 1)
        self.assertEqual(self.client.post(self.url, {**self.dados, "valor": "99"}, format="json").status_code, 409)

    def test_aceita_segundo_boleto_com_valor_e_vencimento_proprios(self):
        resposta = self.client.post(self.url, {**self.dados, "parcela_numero": 2, "valor": "50.99", "data_vencimento": "2026-12-17", "codigo_barras": ""}, format="json")
        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.assertEqual(resposta.data["boleto"]["valor"], "50.99")
        self.assertEqual(resposta.data["boleto"]["parcela_numero"], 2)
        self.assertEqual(resposta.data["boleto"]["total_boletos"], 4)
        self.assertEqual(LancamentoFinanceiro.objects.count(), 1)

    def test_numeracao_invalida_nao_grava(self):
        for valores in ({"parcela_numero": 5}, {"parcela_numero": 0}, {"total_boletos": 0}, {"total_boletos": 1.5}):
            resposta = self.client.post(self.url, {**self.dados, **valores}, format="json")
            self.assertEqual(resposta.status_code, 400)
        self.assertFalse(LancamentoFinanceiro.objects.exists())
        self.client.force_authenticate(None)
        self.assertEqual(self.client.post(self.url, self.dados, format="json").status_code, 401)

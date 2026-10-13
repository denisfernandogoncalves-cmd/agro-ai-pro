from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from apps.accounts.models import AcessoUsuario
from .models import LancamentoFinanceiro, ParceiroFinanceiro


class ContadoresAbasTests(APITestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user("abas-financeiro", is_staff=True)
        self.client.force_authenticate(self.usuario)
        self.parceiro = ParceiroFinanceiro.objects.create(nome="Parceiro abas", tipo="ambos")
        for tipo, status in [("pagar", "pendente"), ("receber", "pendente"), ("pagar", "liquidado"), ("receber", "cancelado")]:
            LancamentoFinanceiro.objects.create(tipo=tipo, status=status, descricao="Safra selecionada", valor="100", valor_liquidado="90" if status == "liquidado" else None, parceiro=self.parceiro, data_vencimento=date(2026, 10, 10))
        LancamentoFinanceiro.objects.create(tipo="pagar", descricao="Outro período", valor="500", data_vencimento=date(2026, 11, 1))
        self.url = reverse("lancamentos-resumo")

    def test_contadores_mantem_filtros_comuns_e_definem_tipo_situacao_por_aba(self):
        params = {"search": "Safra", "parceiro": self.parceiro.pk, "vencimento_inicio": "2026-10-01", "vencimento_fim": "2026-10-31"}
        for tipo, status in [("", ""), ("pagar", "pendente"), ("receber", "pendente"), ("", "liquidado")]:
            with self.subTest(tipo=tipo, status=status):
                resposta = self.client.get(self.url, {**params, "tipo": tipo, "status": status})
                self.assertEqual(resposta.status_code, 200)
                self.assertEqual(resposta.data["contagens_abas"], {"todos": 4, "pagar": 1, "receber": 1, "liquidados": 1})
        resposta = self.client.get(self.url, {**params, "tipo": "pagar", "status": "pendente"})
        self.assertEqual(Decimal(resposta.data["a_pagar"]), Decimal("100"))
        self.assertEqual(Decimal(resposta.data["saidas_realizadas"]), Decimal("0"))

    def test_consulta_vazia_e_periodo_invalido(self):
        resposta = self.client.get(self.url, {"search": "inexistente"})
        self.assertEqual(resposta.data["contagens_abas"], {"todos": 0, "pagar": 0, "receber": 0, "liquidados": 0})
        self.assertEqual(self.client.get(self.url, {"vencimento_inicio": "2026-10-20", "vencimento_fim": "2026-10-01"}).status_code, 400)

    def test_contadores_exigem_acesso_financeiro(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(self.url).status_code, 401)
        restrito = get_user_model().objects.create_user("sem-financeiro")
        AcessoUsuario.objects.create(usuario=restrito, modulos=["cargas"])
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + str(RefreshToken.for_user(restrito).access_token))
        self.assertEqual(self.client.get(self.url).status_code, 403)

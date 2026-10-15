from datetime import date

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from .models import Caminhao, LancamentoTransporte, RemuneracaoMotorista


class EdicaoTransportesTests(APITestCase):
    def setUp(self):
        self.client.force_authenticate(get_user_model().objects.create_user("edicao-transporte"))
        self.caminhao = Caminhao.objects.create(placa="ABC1D23", veiculo="Volvo", motorista="Ana")

    def test_versao_obsoleta_ausente_e_valida_em_todos_os_cadastros(self):
        lancamento = LancamentoTransporte.objects.create(
            caminhao=self.caminhao, motorista="Ana", data=date(2026, 10, 1),
            tipo="receita", descricao="Carga", quantidade=1, valor_unitario=100,
        )
        remuneracao = RemuneracaoMotorista.objects.create(
            caminhao=self.caminhao, motorista="Ana", competencia=date(2026, 10, 1),
            salario=100, comissao_percentual=10,
        )
        for recurso, item, campo, valor in (
            ("caminhoes", self.caminhao, "veiculo", "Scania"),
            ("lancamentos", lancamento, "descricao", "Carga corrigida"),
            ("remuneracoes", remuneracao, "observacoes", "Conferido"),
        ):
            with self.subTest(recurso=recurso):
                url = f"/api/transportes/{recurso}/{item.pk}/"
                versao = self.client.get(url).data["versao_correcao"]
                self.assertEqual(self.client.patch(url, {campo: valor}, format="json").status_code, 400)
                resposta = self.client.patch(url, {campo: valor, "versao_correcao_original": versao}, format="json")
                self.assertEqual(resposta.status_code, 200, resposta.data)
                self.assertNotEqual(resposta.data["versao_correcao"], versao)
                resposta = self.client.patch(url, {campo: "Sobrescrito", "versao_correcao_original": versao}, format="json")
                self.assertEqual(resposta.status_code, 409)
                item.refresh_from_db()
                self.assertEqual(getattr(item, campo), valor)

    def test_criacao_continua_sem_versao_e_put_exige_versao(self):
        resposta = self.client.post("/api/transportes/caminhoes/", {
            "placa": "DEF4G56", "veiculo": "Volvo", "motorista": "Bia", "ativo": True,
        }, format="json")
        self.assertEqual(resposta.status_code, 201)
        url = f'/api/transportes/caminhoes/{resposta.data["id"]}/'
        dados = dict(resposta.data)
        dados["veiculo"] = "Novo"
        self.assertEqual(self.client.put(url, dados, format="json").status_code, 400)
        dados["versao_correcao_original"] = resposta.data["versao_correcao"]
        self.assertEqual(self.client.put(url, dados, format="json").status_code, 200)

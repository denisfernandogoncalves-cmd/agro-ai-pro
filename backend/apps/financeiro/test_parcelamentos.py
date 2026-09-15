from datetime import date
from decimal import Decimal
from unittest.mock import patch
import uuid

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import SimpleTestCase
from rest_framework.test import APITestCase

from .models import LancamentoFinanceiro, ParcelamentoFinanceiro
from .parcelamentos import calcular_parcelas
from .services import liquidar_lancamento


class CalculoParcelasTests(SimpleTestCase):
    def test_centavos_e_fim_de_mes_sem_deslocar_dia_original(self):
        parcelas = calcular_parcelas(Decimal("100.00"), 3, date(2028, 1, 31))
        self.assertEqual([p["valor"] for p in parcelas], [Decimal("33.34"), Decimal("33.33"), Decimal("33.33")])
        self.assertEqual([p["data_vencimento"] for p in parcelas], [date(2028, 1, 31), date(2028, 2, 29), date(2028, 3, 31)])
        self.assertEqual(sum(p["valor"] for p in parcelas), Decimal("100"))

    def test_dezembro_e_fevereiro_nao_bissexto(self):
        parcelas = calcular_parcelas(Decimal("0.03"), 3, date(2026, 12, 31))
        self.assertEqual([p["data_vencimento"] for p in parcelas], [date(2026, 12, 31), date(2027, 1, 31), date(2027, 2, 28)])
        self.assertTrue(all(p["valor"] == Decimal("0.01") for p in parcelas))


class ParcelamentoAPITests(APITestCase):
    def setUp(self):
        self.client.force_authenticate(get_user_model().objects.create_user(username="parcelas"))
        self.url = "/api/financeiro/lancamentos/parcelar/"
        self.dados = {
            "idempotency_key": str(uuid.uuid4()), "tipo": "pagar", "descricao": "Compra de sementes",
            "recebedor_nome": "Recebedor de teste", "valor_total": "100.00", "quantidade": 3,
            "primeiro_vencimento": "2028-01-31", "data_emissao": "2026-09-12",
        }

    def test_cria_parcelas_sem_campos_removidos_e_replay_nao_duplica(self):
        resposta = self.client.post(self.url, self.dados, format="json")
        self.assertEqual(resposta.status_code, 201, resposta.data)
        parcelas = resposta.data["parcelas"]
        self.assertEqual([p["valor"] for p in parcelas], ["33.34", "33.33", "33.33"])
        self.assertEqual([p["parcela_numero"] for p in parcelas], [1, 2, 3])
        self.assertTrue(all(p["categoria"] is None and p["recebedor_nome"] == "Recebedor de teste" for p in parcelas))
        replay = self.client.post(self.url, self.dados, format="json")
        self.assertEqual(replay.status_code, 200)
        self.assertTrue(replay.data["replay"])
        self.assertEqual(LancamentoFinanceiro.objects.count(), 3)
        conflito = self.client.post(self.url, {**self.dados, "valor_total": "120"}, format="json")
        self.assertEqual(conflito.status_code, 409)
        lista = self.client.get("/api/financeiro/lancamentos/", {"search": "Recebedor de teste"})
        self.assertEqual(len(lista.data), 3)
        liquidado = liquidar_lancamento(LancamentoFinanceiro.objects.first(), data_liquidacao=date(2028, 1, 31), valor_liquidado="33.34")
        self.assertEqual(liquidado.status, "liquidado")

    def test_validacao_nao_grava_parcial(self):
        for alteracao in ({"quantidade": 0}, {"quantidade": 121}, {"quantidade": "1.5"},
                          {"recebedor_nome": " "}, {"valor_total": "0.02"}, {"valor_total": "1.001"},
                          {"primeiro_vencimento": "2026-02-30"}, {"primeiro_vencimento": "9999-12-31"},
                          {"codigo_barras": "00197100000000123451234567890123456789012345"}):
            with self.subTest(alteracao=alteracao):
                resposta = self.client.post(self.url, {**self.dados, **alteracao}, format="json")
                self.assertEqual(resposta.status_code, 400, resposta.data)
        self.assertFalse(ParcelamentoFinanceiro.objects.exists())
        self.assertFalse(LancamentoFinanceiro.objects.exists())

    def test_rollback_se_segunda_parcela_falhar(self):
        original = LancamentoFinanceiro.save
        def falhar_segunda(instancia, *args, **kwargs):
            if instancia.parcela_numero == 2:
                raise IntegrityError("Falha simulada")
            return original(instancia, *args, **kwargs)
        with patch.object(LancamentoFinanceiro, "save", falhar_segunda), self.assertRaises(IntegrityError):
            self.client.post(self.url, self.dados, format="json")
        self.assertFalse(ParcelamentoFinanceiro.objects.exists())
        self.assertFalse(LancamentoFinanceiro.objects.exists())

    def test_uma_parcela_preserva_codigo_e_login_obrigatorio(self):
        resposta = self.client.post(self.url, {**self.dados, "quantidade": 1,
            "codigo_barras": "00197100000000123451234567890123456789012345"}, format="json")
        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.assertEqual(resposta.data["parcelas"][0]["codigo_barras"], "00197100000000123451234567890123456789012345")
        self.client.force_authenticate(None)
        self.assertEqual(self.client.post(self.url, self.dados, format="json").status_code, 401)

    def test_relatorio_aceita_categoria_nula_e_mostra_recebedor(self):
        self.client.post(self.url, self.dados, format="json")
        from apps.relatorios.selectors import _financeiro
        linhas = _financeiro({})
        self.assertEqual(len(linhas), 3)
        self.assertTrue(all(linha["categoria"] == "" and linha["parceiro"] == "Recebedor de teste" for linha in linhas))

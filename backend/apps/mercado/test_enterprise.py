from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from .enterprise_analysis import resumo_ativo, serie_ativo
from .enterprise_models import (
    AtivoMercado,
    AtualizacaoMercado,
    ConfiguracaoAtivoMercado,
    CotacaoAtivoMercado,
)
from .enterprise_providers import buscar_ptax, buscar_stooq
from .enterprise_update import (
    ServicoMercadoEnterpriseError,
    atualizar_ativo,
    inicializar_configuracoes,
)


COTACAO_CSV = """Symbol,Date,Time,Open,High,Low,Close,Volume
ZS.F,2026-07-27,10:15:00,1050.00,1070.00,1042.00,1062.50,125000
"""
HISTORICO_CSV = """Date,Open,High,Low,Close,Volume
2026-07-24,1030.00,1052.00,1020.00,1040.00,100000
2026-07-25,1040.00,1060.00,1035.00,1050.00,110000
2026-07-27,1050.00,1070.00,1042.00,1062.50,125000
"""


def transporte_stooq(url):
    return HISTORICO_CSV if "/q/d/l/" in url else COTACAO_CSV


def transporte_ptax(_url):
    return {
        "value": [
            {"cotacaoVenda": 5.42, "dataHoraCotacao": "2026-07-24T13:00:00"},
            {"cotacaoVenda": 5.47, "dataHoraCotacao": "2026-07-25T13:00:00"},
        ]
    }


class ProvedoresMercadoTests(TestCase):
    def test_stooq_retorna_snapshot_e_historico(self):
        snapshot, diarios = buscar_stooq(
            AtivoMercado.SOJA_CBOT,
            transport=transporte_stooq,
        )
        self.assertEqual(str(snapshot["fechamento"]), "1062.50")
        self.assertEqual(len(diarios), 3)
        self.assertEqual(str(diarios[0]["fechamento"]), "1040.00")

    def test_ptax_retorna_serie_sem_chave(self):
        snapshot, diarios = buscar_ptax(transport=transporte_ptax)
        self.assertEqual(str(snapshot["fechamento"]), "5.47")
        self.assertEqual(len(diarios), 2)


class AtualizacaoMercadoTests(TestCase):
    def setUp(self):
        cache.clear()
        inicializar_configuracoes()

    def test_atualiza_snapshot_diario_e_agendamento(self):
        resultado = atualizar_ativo(
            AtivoMercado.SOJA_CBOT,
            force=True,
            text_transport=transporte_stooq,
        )
        configuracao = ConfiguracaoAtivoMercado.objects.get(ativo=AtivoMercado.SOJA_CBOT)
        self.assertFalse(resultado["ignorada"])
        self.assertEqual(CotacaoAtivoMercado.objects.filter(ativo=AtivoMercado.SOJA_CBOT).count(), 4)
        self.assertEqual(configuracao.status, ConfiguracaoAtivoMercado.Status.ATUALIZADO)
        self.assertEqual(configuracao.total_chamadas, 2)
        self.assertGreater(configuracao.proxima_atualizacao, configuracao.ultima_atualizacao)
        self.assertEqual(AtualizacaoMercado.objects.filter(status="sucesso").count(), 1)

    def test_nao_repete_chamada_dentro_da_frequencia(self):
        transporte = Mock(side_effect=transporte_stooq)
        atualizar_ativo(
            AtivoMercado.SOJA_CBOT,
            force=True,
            text_transport=transporte,
        )
        resultado = atualizar_ativo(
            AtivoMercado.SOJA_CBOT,
            force=False,
            text_transport=transporte,
        )
        self.assertTrue(resultado["ignorada"])
        self.assertEqual(transporte.call_count, 2)

    def test_falha_preserva_ultima_cotacao(self):
        atualizar_ativo(
            AtivoMercado.SOJA_CBOT,
            force=True,
            text_transport=transporte_stooq,
        )
        quantidade = CotacaoAtivoMercado.objects.count()
        with self.assertRaises(ServicoMercadoEnterpriseError):
            atualizar_ativo(
                AtivoMercado.SOJA_CBOT,
                force=True,
                text_transport=Mock(side_effect=TimeoutError()),
            )
        configuracao = ConfiguracaoAtivoMercado.objects.get(ativo=AtivoMercado.SOJA_CBOT)
        self.assertEqual(CotacaoAtivoMercado.objects.count(), quantidade)
        self.assertEqual(configuracao.status, ConfiguracaoAtivoMercado.Status.ERRO)
        self.assertEqual(configuracao.falhas_consecutivas, 1)
        self.assertNotIn("https://", configuracao.mensagem_erro)

    def test_resumo_e_series_usam_dados_persistidos(self):
        atualizar_ativo(
            AtivoMercado.SOJA_CBOT,
            force=True,
            text_transport=transporte_stooq,
        )
        resumo = resumo_ativo(AtivoMercado.SOJA_CBOT)
        self.assertTrue(resumo["disponivel"])
        self.assertEqual(str(resumo["cotacao_atual"]), "1062.500000")
        self.assertGreaterEqual(len(serie_ativo(AtivoMercado.SOJA_CBOT, "5d")), 2)

    @override_settings(MERCADO_AUTOMATIC_UPDATE_ENABLED=True)
    @patch("apps.mercado.management.commands.atualizar_mercado.atualizar_mercado_pendente")
    def test_management_command_executa_ciclo_unico(self, atualizar_mock):
        atualizar_mock.return_value = {"atualizadas": 1, "ignoradas": 0, "erros": 0}
        call_command("atualizar_mercado", limit=5)
        atualizar_mock.assert_called_once_with(limite=5)


class MercadoEnterpriseAPITests(APITestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(
            username="mercado-enterprise",
            password="senha-de-teste",
        )
        self.client.force_authenticate(self.usuario)
        inicializar_configuracoes()
        atualizar_ativo(
            AtivoMercado.SOJA_CBOT,
            force=True,
            text_transport=transporte_stooq,
        )

    def test_painel_e_serie_exigem_autenticacao_e_retornam_dados(self):
        painel = self.client.get("/api/mercado/cotacoes-enterprise/painel/")
        serie = self.client.get(
            "/api/mercado/cotacoes-enterprise/serie/",
            {"ativo": AtivoMercado.SOJA_CBOT, "janela": "5d"},
        )
        self.assertEqual(painel.status_code, status.HTTP_200_OK)
        self.assertEqual(serie.status_code, status.HTTP_200_OK)
        self.assertEqual(len(painel.data["ativos"]), 7)
        self.assertGreaterEqual(len(serie.data), 2)

    @patch("apps.mercado.enterprise_views.atualizar_todos")
    def test_atualizacao_manual_reutiliza_servico(self, atualizar_mock):
        atualizar_mock.return_value = {"resultados": [], "erros": []}
        resposta = self.client.post("/api/mercado/cotacoes-enterprise/atualizar/", {}, format="json")
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        atualizar_mock.assert_called_once_with(force=True)

    def test_configuracao_nao_pode_ser_criada_ou_excluida(self):
        configuracao = ConfiguracaoAtivoMercado.objects.first()
        self.assertEqual(
            self.client.post("/api/mercado/configuracoes-enterprise/", {}, format="json").status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
        self.assertEqual(
            self.client.delete(f"/api/mercado/configuracoes-enterprise/{configuracao.pk}/").status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def test_respostas_nao_expoem_credenciais(self):
        resposta = self.client.get("/api/mercado/cotacoes-enterprise/painel/")
        conteudo = str(resposta.data).lower()
        self.assertNotIn("apikey", conteudo)
        self.assertNotIn("authorization", conteudo)
        self.assertNotIn("token", conteudo)

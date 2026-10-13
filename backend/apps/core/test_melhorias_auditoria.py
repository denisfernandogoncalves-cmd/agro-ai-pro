from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.throttles import AutenticacaoThrottle
from apps.core.auditoria import contexto_auditoria
from apps.core.models import RegistroAlteracao
from apps.financeiro.models import LancamentoFinanceiro
from apps.propriedades.models import Propriedade
from apps.transportes.models import Caminhao, LancamentoTransporte, RemuneracaoMotorista


class MelhoriasAuditoriaTests(APITestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user("auditoria-tecnica", is_staff=True)
        self.client.force_authenticate(self.usuario)

    def test_readiness_responde_sem_dados_internos(self):
        resposta = self.client.get("/api/ready/")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json(), {"status": "ok"})
        self.assertIn("no-cache", resposta["Cache-Control"])
        with patch("apps.core.health.connection.cursor", side_effect=RuntimeError("credencial privada")):
            resposta = self.client.get("/api/ready/")
        self.assertEqual(resposta.status_code, 503)
        self.assertNotIn("credencial", resposta.content.decode())

    def test_cache_indisponivel_recebe_503_sem_dados_internos(self):
        with patch("django.core.cache.cache.get", side_effect=RuntimeError("credencial privada")):
            resposta = self.client.get("/api/ready/")
            self.assertEqual(resposta.status_code, 503)
            self.client.force_authenticate(None)
            resposta = self.client.post("/api/auth/token/", {"username": "teste", "password": "teste"})
            self.assertEqual(resposta.status_code, 503)
            self.assertNotIn("credencial", resposta.content.decode())

    def test_filtros_invalidos_recebem_400(self):
        for url in (
            "/api/clima/previsoes/?data_inicio=2026-02-31",
            "/api/clima/previsoes/?propriedade=texto",
            "/api/clima/previsoes/?data_inicio=2026-12-01&data_fim=2026-01-01",
            "/api/financeiro/lancamentos/?parceiro=texto",
            "/api/estoque/lotes/?produto=texto",
            "/api/maquinas/maquinas/?propriedade=texto",
            "/api/producao/operacoes/?talhao=texto",
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 400)

    def test_paginacao_opcional_preserva_listas_e_limita_paginas(self):
        for numero in range(7):
            Propriedade.objects.create(nome=f"Fazenda {numero}", proprietario="Teste", municipio="Teste", uf="PR", area_hectares="10")
        # Propriedades mantêm o contrato antigo e oferecem paginação sob demanda.
        self.assertIsInstance(self.client.get("/api/propriedades/").data, list)
        resposta = self.client.get("/api/propriedades/?page=1&page_size=2")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.data["count"], 7)
        self.assertEqual(len(resposta.data["results"]), 2)
        self.assertIsNotNone(resposta.data["next"])
        self.assertEqual(self.client.get("/api/propriedades/?page_size=-1").status_code, 400)

    def test_financeiro_exige_versao_e_preserva_registro(self):
        item = LancamentoFinanceiro.objects.create(tipo="pagar", descricao="Original", valor="100", data_vencimento=timezone.localdate())
        url = f"/api/financeiro/lancamentos/{item.pk}/"
        self.assertEqual(self.client.patch(url, {"descricao": "Obsoleto"}, format="json").status_code, 400)
        item.refresh_from_db()
        self.assertEqual(item.descricao, "Original")
        versao = item.atualizado_em.isoformat()
        self.assertEqual(self.client.patch(url, {"descricao": "Atual", "atualizado_em_original": versao}, format="json").status_code, 200)
        self.assertEqual(self.client.patch(url, {"descricao": "Obsoleto", "atualizado_em_original": versao}, format="json").status_code, 409)

    def test_transportes_tem_historico_em_api_e_scripts(self):
        resposta = self.client.post("/api/transportes/caminhoes/", {"placa": "ABC1D23", "veiculo": "Teste", "motorista": "Operador"}, format="json")
        self.assertEqual(resposta.status_code, 201)
        self.assertTrue(RegistroAlteracao.objects.filter(modulo="transportes", registro_id=str(resposta.data["id"])).exists())
        with contexto_auditoria(self.usuario, "transportes"):
            caminhao = Caminhao.objects.get(pk=resposta.data["id"])
            caminhao.motorista = "Outro operador"
            caminhao.save()
        registro = RegistroAlteracao.objects.filter(modulo="transportes", acao="editar").first()
        self.assertEqual(registro.alteracoes["motorista"]["depois"], "Outro operador")

    def test_constraints_transportes_protegem_escrita_direta(self):
        caminhao = Caminhao.objects.create(placa="ABC1D23", veiculo="Teste", motorista="Operador")
        for campo, valor in (("quantidade", "-1"), ("valor_unitario", "-1")):
            dados = {"caminhao": caminhao, "motorista": "Operador", "data": date(2026, 1, 1), "tipo": "receita", "descricao": "Teste", "quantidade": "1", "valor_unitario": "1"}
            dados[campo] = valor
            with self.subTest(campo=campo), self.assertRaises(IntegrityError), transaction.atomic():
                LancamentoTransporte.objects.create(**dados)
        with self.assertRaises(IntegrityError), transaction.atomic():
            RemuneracaoMotorista.objects.create(caminhao=caminhao, motorista="Operador", competencia=date(2026, 1, 1), comissao_percentual="101")

    @override_settings(AUTH_LOGIN_RATE="100/min", AUTH_ACCOUNT_RATE="2/min")
    def test_login_limitado_por_conta_e_recupera_apos_janela(self):
        cache.clear()
        self.client.force_authenticate(None)
        dados = {"username": "conta-ficticia-auditoria", "password": "ficticio"}
        try:
            with patch("rest_framework.throttling.time.time", return_value=1000):
                self.assertEqual(self.client.post("/api/auth/token/", dados).status_code, 401)
                self.assertEqual(self.client.post("/api/auth/token/", dados).status_code, 401)
                resposta = self.client.post("/api/auth/token/", dados)
                self.assertEqual(resposta.status_code, 429)
                self.assertIn("Retry-After", resposta)
            with patch("rest_framework.throttling.time.time", return_value=1061):
                self.assertEqual(self.client.post("/api/auth/token/", dados).status_code, 401)
        finally:
            cache.clear()

    def test_ip_encaminhado_so_e_aceito_de_proxy_confiavel(self):
        request = type("Request", (), {"META": {"REMOTE_ADDR": "192.0.2.1", "HTTP_X_REAL_IP": "198.51.100.1"}})()
        self.assertEqual(AutenticacaoThrottle().origem(request), "192.0.2.1")
        with override_settings(AUTH_TRUSTED_PROXY_NETWORKS=("192.0.2.0/24",)):
            self.assertEqual(AutenticacaoThrottle().origem(request), "198.51.100.1")

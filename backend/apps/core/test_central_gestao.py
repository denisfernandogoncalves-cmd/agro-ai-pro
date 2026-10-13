from decimal import Decimal
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase
from apps.accounts.models import AcessoUsuario
from apps.financeiro.models import LancamentoFinanceiro
from apps.graos.models import ArmazemGraos, EntradaProducaoTerceiro
from apps.core.models import AnexoLancamento


class CentralGestaoTests(APITestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(username="gestor", is_staff=True)
        self.client.force_authenticate(self.usuario)
        self.armazem = ArmazemGraos.objects.create(nome="Externo", capacidade_kg=100000)

    def deposito(self, nome="Pessoa código distinto", **campos):
        return EntradaProducaoTerceiro.objects.create(depositante=nome, cultura="Soja", safra="2026", armazem=self.armazem,
                                                     peso_liquido_kg=100, saldo_kg=100, criado_por=self.usuario, **campos)

    def test_documentos_filtram_antes_de_paginar_sem_unir_nomes(self):
        entradas = [self.deposito(documento=str(n)) for n in range(27)]
        r = self.client.get("/api/core/documentos/", {"tipo": "terceiro", "busca": "Pessoa", "pagina": 2})
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["total"], 27)
        self.assertEqual(len(r.data["resultados"]), 2)
        self.assertTrue(all(d["doc_imprimir"] for d in r.data["resultados"]))
        r = self.client.get("/api/core/documentos/", {"tipo": "terceiro", "busca": f"#{entradas[0].pk}"})
        self.assertEqual(r.data["total"], 1)

    def test_union_completa_documentos_e_anexos(self):
        self.deposito()
        AnexoLancamento.objects.create(entidade="financeiro", registro_id="1", nome="Recibo.pdf", tipo="application/pdf", tamanho=1, sha256="a"*64, conteudo=b"x", criado_por=self.usuario)
        r = self.client.get("/api/core/documentos/")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["total"], 2)
        self.assertEqual({d["doc_tipo"] for d in r.data["resultados"]}, {"terceiro", "anexo"})

    def test_documentos_preservam_permissoes_de_origem_e_impressao(self):
        self.deposito()
        self.usuario.is_staff = False
        self.usuario.save()
        acesso = AcessoUsuario.objects.create(usuario=self.usuario, modulos=["relatorios"], permissoes={"relatorios":["consultar"]})
        self.assertEqual(self.client.get("/api/core/documentos/").data["total"], 0)
        acesso.modulos = ["cargas"]
        acesso.permissoes = {"cargas":["consultar"]}
        acesso.save()
        r = self.client.get("/api/core/documentos/")
        self.assertEqual(r.data["total"], 1)
        self.assertFalse(r.data["resultados"][0]["doc_imprimir"])
        self.assertEqual(self.client.get("/api/core/conferencia-financeira/").status_code, 403)

    def test_financeiro_nao_compensa_diferencas_nem_altera_titulos(self):
        for valor, pago, status in [(100, 60, "liquidado"), (100, 120, "liquidado"), (100, 100, "liquidado"), (100, None, "pendente")]:
            LancamentoFinanceiro.objects.create(tipo="pagar", descricao="Conferir boleto", valor=valor, valor_liquidado=pago,
                status=status, data_vencimento=timezone.localdate(), data_liquidacao=timezone.localdate() if pago else None)
        r = self.client.get("/api/core/conferencia-financeira/")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["total"], 2)
        self.assertEqual(r.data["resumo"], {"a_menor":Decimal("40"), "a_maior":Decimal("20")})
        self.assertEqual(LancamentoFinanceiro.objects.filter(status="pendente").count(), 1)

    def test_validacao_datas_e_paginacao(self):
        for params in ({"inicio":"2026-10-08","fim":"2026-10-07"}, {"pagina":0}, {"tipo":"invalido"}):
            self.assertEqual(self.client.get("/api/core/documentos/", params).status_code, 400)

    def test_diagnostico_privado_sem_segredos_e_falha_banco(self):
        with patch("apps.core.central_gestao.situacao_backup", return_value={"situacao":"em_dia"}):
            r = self.client.get("/api/core/diagnostico/")
        self.assertEqual(r.data["banco"], "ok")
        self.assertIn("backup", r.data)
        self.usuario.is_staff = False
        self.usuario.save()
        with patch("apps.core.central_gestao.connection.cursor", side_effect=RuntimeError("segredo")):
            r = self.client.get("/api/core/diagnostico/")
        self.assertEqual(r.data["banco"], "indisponivel")
        self.assertNotIn("backup", r.data)
        self.assertNotIn("segredo", str(r.data))
        self.client.force_authenticate(None)
        for caminho in ("diagnostico", "documentos", "conferencia-financeira"):
            self.assertEqual(self.client.get(f"/api/core/{caminho}/").status_code, 401)

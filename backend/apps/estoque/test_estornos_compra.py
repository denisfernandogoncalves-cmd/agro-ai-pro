import uuid
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless
from unittest.mock import patch

from django.db import connection, close_old_connections
from rest_framework.test import APITestCase, APITransactionTestCase

from . import test_compras
from .models import CompraEstoque, EstornoCompraEstoque, MovimentacaoEstoque
from .services import saldo_lote, registrar_movimentacao
from .compras import estornar_compra, CompraConflitante


class EstornosCompraTests(APITestCase):
    setUp = test_compras.CompraEstoqueTests.setUp

    def registrar(self):
        resposta = self.client.post(self.url, self.dados, format="json")
        self.assertEqual(resposta.status_code, 201, resposta.data)
        return CompraEstoque.objects.get(pk=self.dados["id"])

    def retirar(self, acao="estornar", **dados):
        payload = {"id": str(uuid.uuid4()), "quantidade": "15.500", "motivo": "Devolução ao fornecedor", "quantidade_estornada_original": "0", **dados}
        return self.client.post(f"{self.url}{self.dados['id']}/{acao}/", payload, format="json")

    def test_parcial_preserva_original_e_historico(self):
        compra = self.registrar()
        resposta = self.retirar()
        self.assertEqual(resposta.status_code, 200, resposta.data)
        self.assertEqual(resposta.data["status_compra"], "estorno_parcial")
        self.assertEqual(Decimal(resposta.data["quantidade_estornada"]), Decimal("15.500"))
        self.assertEqual(Decimal(resposta.data["quantidade_restante"]), Decimal("699.500"))
        self.assertEqual(saldo_lote(compra.movimento.lote), Decimal("699.500"))
        compra.refresh_from_db()
        self.assertEqual(compra.movimento.quantidade, Decimal("715"))
        self.assertEqual(compra.valor_total, Decimal("52910"))
        estorno = EstornoCompraEstoque.objects.get()
        self.assertEqual(estorno.criado_por, self.usuario)
        self.assertEqual(estorno.movimento.tipo, "saida")
        self.assertEqual(resposta.data["estornos"][0]["motivo"], "Devolução ao fornecedor")

    def test_cancelamento_total_e_parcial_seguido_de_cancelamento(self):
        compra = self.registrar()
        self.assertEqual(self.retirar().status_code, 200)
        resposta = self.retirar("cancelar", quantidade_estornada_original="15.500")
        self.assertEqual(resposta.status_code, 200, resposta.data)
        self.assertEqual(resposta.data["status_compra"], "cancelada")
        self.assertEqual(saldo_lote(compra.movimento.lote), 0)
        self.assertEqual(EstornoCompraEstoque.objects.count(), 2)
        self.assertEqual(EstornoCompraEstoque.objects.get(cancelamento=True).quantidade, Decimal("699.500"))
        self.assertEqual(self.retirar("cancelar", quantidade_estornada_original="715").status_code, 409)

    def test_cancelamento_direto(self):
        compra = self.registrar()
        resposta = self.retirar("cancelar")
        self.assertEqual(resposta.status_code, 200, resposta.data)
        self.assertEqual(resposta.data["status_compra"], "cancelada")
        self.assertEqual(saldo_lote(compra.movimento.lote), 0)

    def test_saldo_consumido_bloqueia_cancelamento_e_excesso(self):
        compra = self.registrar()
        registrar_movimentacao(usuario=self.usuario, lote=compra.movimento.lote, tipo="saida", quantidade="700")
        self.assertEqual(self.retirar("cancelar").status_code, 400)
        self.assertEqual(self.retirar(quantidade="15.001").status_code, 400)
        self.assertFalse(EstornoCompraEstoque.objects.exists())
        self.assertEqual(self.retirar(quantidade="15").status_code, 200)
        self.assertEqual(saldo_lote(compra.movimento.lote), 0)

    def test_validacao_quantidade_motivo_e_versao(self):
        self.registrar()
        for quantidade in ("0", "-1", "716", "1.0001", "NaN", "Infinity"):
            with self.subTest(quantidade=quantidade):
                self.assertEqual(self.retirar(quantidade=quantidade).status_code, 400)
        self.assertEqual(self.retirar(motivo="  ").status_code, 400)
        self.assertEqual(self.retirar(motivo="x" * 501).status_code, 400)
        self.assertEqual(self.retirar(quantidade_estornada_original="1").status_code, 409)
        self.assertFalse(EstornoCompraEstoque.objects.exists())

    def test_reenvio_idempotente_e_chave_conflitante(self):
        compra = self.registrar()
        chave = str(uuid.uuid4())
        self.assertEqual(self.retirar(id=chave).status_code, 200)
        self.assertEqual(self.retirar(id=chave).status_code, 200)
        self.assertEqual(self.retirar(id=chave, quantidade="12").status_code, 409)
        self.assertEqual(EstornoCompraEstoque.objects.count(), 1)
        self.assertEqual(saldo_lote(compra.movimento.lote), Decimal("699.5"))
        self.assertEqual(self.retirar().status_code, 409)

    def test_historico_nao_pode_ser_apagado_ou_corrigido_pela_movimentacao(self):
        self.registrar()
        self.retirar()
        estorno = EstornoCompraEstoque.objects.get()
        self.assertEqual(self.client.delete(f"{self.url}{self.dados['id']}/").status_code, 409)
        self.assertEqual(self.client.delete(f"/api/estoque/movimentacoes/{estorno.movimento_id}/").status_code, 409)
        from apps.core.correcoes import versao_correcao
        resposta = self.client.patch(f"/api/estoque/movimentacoes/{estorno.movimento_id}/corrigir/",
            {"quantidade": "1", "motivo_correcao": "teste", "versao_correcao_original": versao_correcao(estorno.movimento)}, format="json")
        self.assertEqual(resposta.status_code, 400, resposta.data)
        self.assertTrue(EstornoCompraEstoque.objects.filter(pk=estorno.pk).exists())

    def test_pagamento_existente_preservado_e_cancelada_bloqueia_novo(self):
        compra = self.registrar()
        compra.data_pagamento = "2026-09-14"
        compra.valor_pago = Decimal("100")
        compra.save()
        self.assertEqual(self.retirar("cancelar").status_code, 200)
        compra.refresh_from_db()
        self.assertEqual(compra.valor_pago, Decimal("100"))
        resposta = self.client.post(f"{self.url}{compra.pk}/pagar/", {"data_pagamento": "2026-10-15", "valor_pago": "10"}, format="json")
        self.assertEqual(resposta.status_code, 409)

    def test_autenticacao_obrigatoria(self):
        self.registrar()
        self.client.force_authenticate(None)
        self.assertEqual(self.retirar().status_code, 401)
        self.assertEqual(self.retirar("cancelar").status_code, 401)

    def test_usuario_somente_consulta_nao_retira_estoque(self):
        self.registrar()
        from apps.accounts.models import AcessoUsuario
        from rest_framework_simplejwt.tokens import AccessToken
        AcessoUsuario.objects.update_or_create(usuario=self.usuario, defaults={"modulos":["estoque"], "permissoes":{"estoque":["consultar"]}})
        self.client.force_authenticate(None)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(self.usuario)}")
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.assertEqual(self.retirar().status_code, 403)
        self.assertEqual(self.retirar("cancelar").status_code, 403)
        self.assertFalse(EstornoCompraEstoque.objects.exists())

    def test_falha_ao_salvar_historico_reverte_saida(self):
        compra = self.registrar()
        with patch.object(EstornoCompraEstoque.objects, "create", side_effect=RuntimeError("falha simulada")):
            with self.assertRaises(RuntimeError):
                self.retirar()
        self.assertEqual(saldo_lote(compra.movimento.lote), Decimal("715"))
        self.assertEqual(MovimentacaoEstoque.objects.count(), 1)


@skipUnless(connection.vendor == "postgresql", "Bloqueios exigem PostgreSQL")
class EstornosConcorrentesTests(APITransactionTestCase):
    setUp = test_compras.CompraEstoqueTests.setUp

    def test_duas_retiradas_obsoletas_nao_duplicam_saldo(self):
        self.client.post(self.url, self.dados, format="json")
        barreira = Barrier(2)
        compra_id, usuario_id = self.dados["id"], self.usuario.pk

        def retirar():
            close_old_connections()
            try:
                from django.contrib.auth import get_user_model
                usuario = get_user_model().objects.get(pk=usuario_id)
                compra = CompraEstoque.objects.select_related("movimento__lote").get(pk=compra_id)
                barreira.wait(timeout=10)
                try:
                    estornar_compra(compra=compra, usuario=usuario, dados={"id":uuid.uuid4(), "motivo":"Devolução", "quantidade":Decimal("400"), "quantidade_estornada_original":Decimal("0")})
                    return "ok"
                except CompraConflitante:
                    return "conflito"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            resultados = list(executor.map(lambda _: retirar(), range(2)))
        self.assertCountEqual(resultados, ["ok", "conflito"])
        self.assertEqual(EstornoCompraEstoque.objects.count(), 1)
        self.assertEqual(saldo_lote(CompraEstoque.objects.get().movimento.lote), Decimal("315"))

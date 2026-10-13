from datetime import date
from decimal import Decimal
from django.utils import timezone
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APITestCase
from apps.accounts.models import AcessoUsuario
from .models import EntregaVendaGraos
from .services import confirmar_venda, registrar_entrega_venda
from .tests import ContextoVendaMixin


class ConsultaSaidasTests(ContextoVendaMixin, APITestCase):
    url = "/api/comercial/romaneios/"

    def setUp(self):
        self.criar_contexto(saldo="10000")
        self.client.force_authenticate(self.usuario)
        self.venda = self.rascunho(quantidade="1000")
        confirmar_venda(usuario=self.usuario, venda=self.venda, chave_idempotencia="confirmar-romaneios")
        self.entregas = []
        for dia in range(1, 8):
            registrar_entrega_venda(usuario=self.usuario, venda=self.venda, quantidade_kg="100",
                chave_idempotencia=f"romaneio-{dia}", data_entrega=date(2026, 10, dia),
                destino="José Comprador", placa="ABC1D23", nota_produtor="00123")
        self.entregas = list(self.venda.entregas.order_by("id"))
        EntregaVendaGraos.objects.filter(pk=self.entregas[-1].pk).update(cancelado_em=timezone.now())

    def test_paginacao_total_global_e_resposta_reduzida(self):
        with CaptureQueriesContext(connection) as consultas:
            resposta = self.client.get(self.url)
        self.assertEqual(resposta.status_code, 200, resposta.data)
        primeira = resposta.data
        segunda = self.client.get(self.url, {"pagina": 2}).data
        self.assertEqual(primeira["total"], 6)
        self.assertEqual(len(primeira["itens"]), 5)
        self.assertEqual(len(segunda["itens"]), 1)
        self.assertEqual(Decimal(primeira["peso_ativo_kg"]), 600)
        self.assertEqual(primeira["peso_ativo_kg"], segunda["peso_ativo_kg"])
        self.assertLessEqual(len(consultas), 6, "Página não deve consultar cada venda separadamente")
        self.assertNotIn("entregas", primeira["itens"][0]["venda"])
        self.assertNotIn("alteracoes", primeira["itens"][0]["venda"])
        self.assertEqual(self.client.get(self.url, {"pagina": 999}).data["pagina"], 2)

    def test_busca_data_da_saida_ordem_e_historico(self):
        for busca in ("jose", "ABC1D23", "00123", f"#{self.entregas[0].pk}"):
            r = self.client.get(self.url, {"busca": busca})
            self.assertEqual(r.status_code, 200, r.data)
            self.assertGreater(r.data["total"], 0)
        r = self.client.get(self.url, {"inicio": "2026-10-02", "fim": "2026-10-03", "ordem": "antigos"}).data
        self.assertEqual([i["saida"]["data_entrega"] for i in r["itens"]], ["2026-10-02", "2026-10-03"])
        h = self.client.get(self.url, {"historico": "true"}).data
        self.assertEqual(h["total"], 7)
        self.assertEqual(Decimal(h["peso_ativo_kg"]), 600)
        self.venda.excluida_em = timezone.now()
        self.venda.save(update_fields=["excluida_em"])
        self.assertEqual(self.client.get(self.url).data["total"], 0)
        h = self.client.get(self.url, {"historico": "true"}).data
        self.assertEqual(h["total"], 7)
        self.assertEqual(Decimal(h["peso_ativo_kg"]), 0)

    def test_parametros_invalidos_vazio_e_permissoes(self):
        for params in ({"inicio": "2026-10-05", "fim": "2026-10-01"}, {"pagina": "0"}, {"por_pagina": "21"}):
            self.assertEqual(self.client.get(self.url, params).status_code, 400)
        vazio = self.client.get(self.url, {"busca": "inexistente"}).data
        self.assertEqual((vazio["total"], vazio["inicio"], vazio["fim"], vazio["itens"]), (0, 0, 0, []))
        AcessoUsuario.objects.create(usuario=self.usuario, modulos=["cargas"])
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get(self.url).status_code, 401)

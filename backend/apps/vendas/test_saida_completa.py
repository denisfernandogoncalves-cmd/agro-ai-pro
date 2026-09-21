from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

from django.db import close_old_connections, connection
from django.test import TransactionTestCase
from rest_framework.test import APIClient, APITestCase

from apps.graos.models import MovimentacaoGraos, ReservaSaldoGraos
from apps.relatorios.selectors import _item_entrega
from .models import AlteracaoVendaGraos, ContratoComercial, EntregaVendaGraos, VendaGraos
from .tests import ContextoVendaMixin


class SaidaCompletaMixin(ContextoVendaMixin):
    url = "/api/comercial/vendas/registrar-saida/"

    def contexto_saida(self):
        self.criar_contexto()
        self.contrato = ContratoComercial.objects.create(
            empresa="Empresa destino", numero="CTR-123", produto="Soja", quantidade_kg="1000",
        )
        self.dados = {
            "contrato": self.contrato.pk, "posicao": self.posicao.pk,
            "quantidade_kg": "200.125", "data_contrato": "2026-08-30",
            "data_movimento": "2026-08-30", "destino": "Unidade compradora",
            "placa": "abc-1d23", "motorista": "  Motorista de teste  ",
            "nota_produtor": "NP-001", "nota_empresa": "NE-002",
        }


class SaidaCompletaTests(SaidaCompletaMixin, APITestCase):
    def setUp(self):
        self.contexto_saida()
        self.client.force_authenticate(self.usuario)

    def enviar(self, dados=None, chave="saida-completa"):
        return self.client.post(self.url, dados or self.dados, format="json", HTTP_IDEMPOTENCY_KEY=chave)

    def test_registra_todos_os_campos_e_baixa_peso_liquido(self):
        resposta = self.enviar()
        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.assertEqual(resposta.data["status"], "entregue")
        self.assertEqual(resposta.data["cad_pro_codigo"], self.cadpro.codigo)
        self.assertEqual(resposta.data["numero_contrato"], "CTR-123")
        entrega = resposta.data["entregas"][0]
        for campo, esperado in {"destino": "Unidade compradora", "placa": "ABC1D23", "motorista": "Motorista de teste", "nota_produtor": "NP-001", "nota_empresa": "NE-002", "quantidade_kg": "200.125", "data_entrega": "2026-08-30"}.items():
            self.assertEqual(entrega[campo], esperado)
        self.posicao.refresh_from_db()
        self.assertEqual(self.posicao.saldo_fisico_kg, Decimal("799.875"))
        self.assertEqual(self.posicao.saldo_comprometido_kg, Decimal("0"))
        self.assertEqual(_item_entrega(EntregaVendaGraos.objects.get(pk=entrega["id"]))["motorista"], "Motorista de teste")

    def test_placa_invalida_nao_deixa_rascunho_nem_reserva(self):
        antes = MovimentacaoGraos.objects.count()
        for alteracao in ({"placa": "ABC"},):
            with self.subTest(alteracao=alteracao):
                resposta = self.enviar({**self.dados, **alteracao})
                self.assertEqual(resposta.status_code, 409, resposta.data)
                self.assertEqual(VendaGraos.objects.count(), 0)
                self.assertEqual(ReservaSaldoGraos.objects.count(), 0)
                self.assertEqual(MovimentacaoGraos.objects.count(), antes)

    def test_repeticao_idempotente_e_mudanca_de_motorista_conflitante(self):
        primeira = self.enviar()
        segunda = self.enviar()
        self.assertEqual(segunda.status_code, 201, segunda.data)
        self.assertEqual(primeira.data["id"], segunda.data["id"])
        self.assertEqual(EntregaVendaGraos.objects.count(), 1)
        resposta = self.enviar({**self.dados, "motorista": "Outro motorista"})
        self.assertEqual(resposta.status_code, 409, resposta.data)
        self.assertEqual(EntregaVendaGraos.objects.count(), 1)

    def test_edicao_de_motorista_preserva_original_e_nao_altera_peso(self):
        resposta = self.enviar()
        venda = resposta.data
        entrega = venda["entregas"][0]
        resposta = self.client.patch(f"/api/comercial/vendas/{venda['id']}/entregas/{entrega['id']}/", {
            "versao": venda["versao"], "motivo": "Corrigir nome", "quantidade_kg": "200.125",
            "motorista": "Nome corrigido",
        }, format="json", HTTP_IDEMPOTENCY_KEY="editar-motorista")
        self.assertEqual(resposta.status_code, 200, resposta.data)
        ativo = next(e for e in resposta.data["entregas"] if not e["cancelado_em"])
        self.assertEqual(ativo["motorista"], "Nome corrigido")
        self.assertEqual(EntregaVendaGraos.objects.get(pk=entrega["id"]).motorista, "Motorista de teste")
        self.assertEqual(AlteracaoVendaGraos.objects.get().antes["entregas"][0]["motorista"], "Motorista de teste")
        self.posicao.refresh_from_db()
        self.assertEqual(self.posicao.saldo_fisico_kg, Decimal("799.875"))

    def test_campos_de_transporte_opcionais_preservam_fluxo_legado(self):
        dados = {k: v for k, v in self.dados.items() if k not in ("motorista", "placa", "nota_produtor", "nota_empresa")}
        self.assertEqual(self.enviar(dados).status_code, 201)
        self.assertEqual(self.enviar(dados).status_code, 201)
        self.assertEqual(EntregaVendaGraos.objects.get().motorista, "")

    def test_exige_autenticacao_chave_e_limite_de_motorista(self):
        self.assertEqual(self.client.post(self.url, self.dados, format="json").status_code, 400)
        self.assertEqual(self.enviar({**self.dados, "motorista": "x" * 161}).status_code, 400)
        self.client.force_authenticate(None)
        self.assertEqual(self.enviar().status_code, 401)
        self.assertEqual(VendaGraos.objects.count(), 0)


class SaidaCompletaConcorrenciaTests(SaidaCompletaMixin, TransactionTestCase):
    def test_migration_compativel_com_coluna_preexistente_preserva_nome(self):
        if connection.vendor != "postgresql":
            self.skipTest("Compatibilidade de coluna existente requer PostgreSQL.")
        from importlib import import_module
        from django.apps import apps
        self.contexto_saida()
        client = APIClient()
        client.force_authenticate(self.usuario)
        resposta = client.post(self.url, self.dados, format="json", HTTP_IDEMPOTENCY_KEY="migration")
        self.assertEqual(resposta.status_code, 201, resposta.data)
        with connection.cursor() as cursor:
            cursor.execute("ALTER TABLE vendas_entregavendagraos ALTER COLUMN motorista TYPE varchar(120)")
        migration = import_module("apps.vendas.migrations.0006_entregavendagraos_motorista")
        with connection.schema_editor() as editor:
            migration.adicionar_motorista(apps, editor)
            migration.preservar_motorista_no_retorno(apps, editor)
            migration.adicionar_motorista(apps, editor)
        self.assertEqual(EntregaVendaGraos.objects.get().motorista, "Motorista de teste")
        with connection.cursor() as cursor:
            cursor.execute("SELECT character_maximum_length FROM information_schema.columns WHERE table_name='vendas_entregavendagraos' AND column_name='motorista'")
            self.assertEqual(cursor.fetchone()[0], 160)

    def test_duas_saidas_sao_debitadas_sem_perder_atualizacoes(self):
        if connection.vendor != "postgresql":
            self.skipTest("Requer bloqueios reais do PostgreSQL.")
        self.contexto_saida()
        barreira = Barrier(2)

        def enviar(chave):
            close_old_connections()
            try:
                client = APIClient()
                client.force_authenticate(self.usuario)
                barreira.wait(timeout=10)
                return client.post(self.url, {**self.dados, "quantidade_kg": "600"}, format="json", HTTP_IDEMPOTENCY_KEY=chave).status_code
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            resultados = list(executor.map(enviar, ("saida-a", "saida-b")))
        self.assertCountEqual(resultados, [201, 201])
        self.assertEqual(VendaGraos.objects.count(), 2)
        self.assertEqual(EntregaVendaGraos.objects.count(), 2)
        self.posicao.refresh_from_db()
        self.assertEqual(self.posicao.saldo_fisico_kg, Decimal("-200"))
        self.assertEqual(self.posicao.saldo_comprometido_kg, Decimal("0"))

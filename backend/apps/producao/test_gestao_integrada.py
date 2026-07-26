from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase

from apps.estoque.models import LocalEstoque
from apps.financeiro.models import ParceiroFinanceiro
from apps.propriedades.models import AcessoPropriedade, Propriedade
from apps.talhoes.models import Talhao

from .grain_models import (
    AcessoCadPro,
    CadPro,
    Cultura,
    EmbarqueProducao,
    ImportacaoPlanilha,
    MovimentacaoGraos,
    RecebimentoProducao,
    Safra,
    SaldoGraos,
)
from .grain_services import (
    ProducaoError,
    confirmar_embarque,
    confirmar_recebimento,
    estornar_embarque,
    registrar_movimentacao,
)


@override_settings(PROPERTY_ACCESS_LEGACY_TEST_MODE=False)
class GestaoIntegradaProducaoTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.gestor = user_model.objects.create_user(username="gestor-producao", password="teste")
        self.leitor = user_model.objects.create_user(username="leitor-producao", password="teste")
        self.externo = user_model.objects.create_user(username="externo-producao", password="teste")
        self.propriedade = Propriedade.objects.create(
            nome="Fazenda Integrada",
            municipio="Ivaiporã",
            uf="PR",
            area_hectares="120.00",
        )
        self.propriedade_externa = Propriedade.objects.create(
            nome="Fazenda Externa",
            municipio="Arapuã",
            uf="PR",
            area_hectares="80.00",
        )
        AcessoPropriedade.objects.create(
            propriedade=self.propriedade,
            usuario=self.gestor,
            papel=AcessoPropriedade.Papel.GESTOR,
        )
        AcessoPropriedade.objects.create(
            propriedade=self.propriedade,
            usuario=self.leitor,
            papel=AcessoPropriedade.Papel.LEITURA,
        )
        AcessoPropriedade.objects.create(
            propriedade=self.propriedade_externa,
            usuario=self.externo,
            papel=AcessoPropriedade.Papel.GESTOR,
        )
        self.cadpro = CadPro.objects.create(
            propriedade=self.propriedade,
            codigo="CAD-001",
            titular="Produtor Teste",
        )
        self.cadpro_externo = CadPro.objects.create(
            propriedade=self.propriedade_externa,
            codigo="CAD-EXT",
            titular="Outro Produtor",
        )
        AcessoCadPro.objects.create(cadpro=self.cadpro, usuario=self.gestor)
        AcessoCadPro.objects.create(cadpro=self.cadpro, usuario=self.leitor)
        AcessoCadPro.objects.create(cadpro=self.cadpro_externo, usuario=self.externo)
        self.cultura = Cultura.objects.create(nome="Soja", codigo="soja", peso_saca_kg="60")
        self.safra = Safra.objects.create(nome="2026/2027")
        self.local = LocalEstoque.objects.create(nome="Silo Principal", propriedade=self.propriedade)
        self.local_destino = LocalEstoque.objects.create(nome="Armazém Secundário", propriedade=self.propriedade)
        self.talhao = Talhao.objects.create(
            propriedade=self.propriedade,
            nome="Talhão Norte",
            area_hectares="20.00",
            cultura_atual="Soja",
            safra="2026/2027",
        )
        self.comprador = ParceiroFinanceiro.objects.create(
            nome="Comprador Teste",
            tipo=ParceiroFinanceiro.Tipo.CLIENTE,
        )

    def criar_recebimento(self, peso="6000.000"):
        return RecebimentoProducao.objects.create(
            propriedade=self.propriedade,
            cadpro=self.cadpro,
            talhao=self.talhao,
            cultura=self.cultura,
            safra=self.safra,
            local_armazenagem=self.local,
            peso_bruto_kg="10000.000",
            tara_kg="3000.000",
            peso_liquido_kg=peso,
            umidade_percentual="12.500",
            impureza_percentual="1.000",
            defeitos_percentual="0.500",
            criado_por=self.gestor,
        )

    def test_confirmacao_de_recebimento_atualiza_saldo_e_sacas(self):
        recebimento = confirmar_recebimento(self.criar_recebimento(), usuario=self.gestor)
        recebimento.refresh_from_db()
        saldo = SaldoGraos.objects.get(cadpro=self.cadpro, local_armazenagem=self.local)
        self.assertEqual(recebimento.status, RecebimentoProducao.Status.CONFIRMADO)
        self.assertEqual(recebimento.quantidade_sacas, Decimal("100.000"))
        self.assertEqual(saldo.quantidade_kg, Decimal("6000.000"))
        self.assertEqual(recebimento.movimentacao.tipo, MovimentacaoGraos.Tipo.ENTRADA)

    def test_saida_nunca_permite_saldo_negativo(self):
        with self.assertRaises(ProducaoError):
            registrar_movimentacao(
                usuario=self.gestor,
                tipo=MovimentacaoGraos.Tipo.SAIDA,
                propriedade=self.propriedade,
                cadpro=self.cadpro,
                talhao=self.talhao,
                cultura=self.cultura,
                safra=self.safra,
                quantidade_kg="1.000",
                local_origem=self.local,
            )
        self.assertFalse(MovimentacaoGraos.objects.exists())

    def test_transferencia_preserva_total(self):
        confirmar_recebimento(self.criar_recebimento(), usuario=self.gestor)
        registrar_movimentacao(
            usuario=self.gestor,
            tipo=MovimentacaoGraos.Tipo.TRANSFERENCIA,
            propriedade=self.propriedade,
            cadpro=self.cadpro,
            talhao=self.talhao,
            cultura=self.cultura,
            safra=self.safra,
            quantidade_kg="1500.000",
            local_origem=self.local,
            local_destino=self.local_destino,
        )
        origem = SaldoGraos.objects.get(cadpro=self.cadpro, local_armazenagem=self.local)
        destino = SaldoGraos.objects.get(cadpro=self.cadpro, local_armazenagem=self.local_destino)
        self.assertEqual(origem.quantidade_kg, Decimal("4500.000"))
        self.assertEqual(destino.quantidade_kg, Decimal("1500.000"))
        self.assertEqual(origem.quantidade_kg + destino.quantidade_kg, Decimal("6000.000"))

    def test_embarque_integra_estoque_e_financeiro_e_estorno_reverte(self):
        confirmar_recebimento(self.criar_recebimento(), usuario=self.gestor)
        embarque = EmbarqueProducao.objects.create(
            propriedade=self.propriedade,
            cadpro=self.cadpro,
            cultura=self.cultura,
            safra=self.safra,
            local_armazenagem=self.local,
            comprador=self.comprador,
            romaneio="ROM-001",
            quantidade_kg="3000.000",
            preco_saca="125.00",
            criado_por=self.gestor,
        )
        embarque = confirmar_embarque(embarque, usuario=self.gestor)
        saldo = SaldoGraos.objects.get(cadpro=self.cadpro, local_armazenagem=self.local)
        self.assertEqual(saldo.quantidade_kg, Decimal("3000.000"))
        self.assertEqual(embarque.valor_total, Decimal("6250.00"))
        self.assertIsNotNone(embarque.lancamento_financeiro_id)
        embarque = estornar_embarque(embarque, usuario=self.gestor, motivo="Erro de romaneio")
        saldo.refresh_from_db()
        embarque.lancamento_financeiro.refresh_from_db()
        self.assertEqual(saldo.quantidade_kg, Decimal("6000.000"))
        self.assertEqual(embarque.status, EmbarqueProducao.Status.ESTORNADO)
        self.assertEqual(embarque.lancamento_financeiro.status, "cancelado")

    def test_usuario_sem_acesso_ao_cadpro_nao_visualiza_recurso(self):
        recebimento = self.criar_recebimento()
        self.client.force_authenticate(self.externo)
        response = self.client.get(f"/api/producao/recebimentos/{recebimento.id}/")
        self.assertEqual(response.status_code, 404)

    def test_somente_leitura_nao_cria_recebimento(self):
        self.client.force_authenticate(self.leitor)
        response = self.client.post(
            "/api/producao/recebimentos/",
            {
                "propriedade": self.propriedade.id,
                "cadpro": self.cadpro.id,
                "talhao": self.talhao.id,
                "cultura": self.cultura.id,
                "safra": self.safra.id,
                "local_armazenagem": self.local.id,
                "peso_bruto_kg": "10000.000",
                "tara_kg": "3000.000",
                "peso_liquido_kg": "6000.000",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_importacao_exige_previa_e_confirmacao(self):
        self.client.force_authenticate(self.gestor)
        arquivo = SimpleUploadedFile(
            "recebimentos.csv",
            (
                "Data;Cultura;Safra;Peso Bruto KG;Peso Liquido KG;Local;Talhao\n"
                "26/07/2026;Soja;2026/2027;10000;6000;Silo Principal;Talhão Norte\n"
            ).encode("utf-8"),
            content_type="text/csv",
        )
        response = self.client.post(
            "/api/producao/importacoes/",
            {
                "tipo": ImportacaoPlanilha.Tipo.RECEBIMENTOS,
                "propriedade": self.propriedade.id,
                "cadpro": self.cadpro.id,
                "arquivo": arquivo,
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 201, response.data)
        importacao = ImportacaoPlanilha.objects.get(pk=response.data["id"])
        self.assertEqual(importacao.status, ImportacaoPlanilha.Status.VALIDADA)
        self.assertFalse(RecebimentoProducao.objects.exists())
        confirmacao = self.client.post(f"/api/producao/importacoes/{importacao.id}/confirmar/", {}, format="json")
        self.assertEqual(confirmacao.status_code, 200, confirmacao.data)
        self.assertEqual(RecebimentoProducao.objects.count(), 1)
        self.assertEqual(RecebimentoProducao.objects.get().status, RecebimentoProducao.Status.RASCUNHO)

    def test_dashboard_e_exportacoes_respeitam_escopo(self):
        confirmar_recebimento(self.criar_recebimento(), usuario=self.gestor)
        self.client.force_authenticate(self.gestor)
        dashboard = self.client.get("/api/producao/dashboard-integrado/")
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(Decimal(str(dashboard.data["producao"]["peso_liquido_kg"])), Decimal("6000.000"))
        for formato, content_type in (
            ("csv", "text/csv"),
            ("xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            ("pdf", "application/pdf"),
        ):
            response = self.client.get(f"/api/producao/relatorios-integrados/?formato={formato}")
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response["Content-Type"].startswith(content_type))

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.estoque.models import LocalEstoque
from apps.financeiro.models import LancamentoFinanceiro, ParceiroFinanceiro
from apps.propriedades.models import AcessoPropriedade, Propriedade

from .grain_access import cadpros_visiveis
from .grain_models import (
    AcessoCadPro,
    AuditoriaProducao,
    CadPro,
    Cultura,
    EmbarqueProducao,
    MovimentacaoGraos,
    RecebimentoProducao,
    Safra,
    SaldoGraos,
)
from .grain_services import (
    ProducaoError,
    confirmar_embarque,
    confirmar_recebimento,
    registrar_movimentacao,
)


@override_settings(PROPERTY_ACCESS_LEGACY_TEST_MODE=False)
class GestaoIntegradaProducaoTests(TestCase):
    def setUp(self):
        usuario_model = get_user_model()
        self.admin = usuario_model.objects.create_user("admin-producao", password="x")
        self.operador = usuario_model.objects.create_user("operador-producao", password="x")
        self.leitura = usuario_model.objects.create_user("leitura-producao", password="x")
        self.externo = usuario_model.objects.create_user("externo-producao", password="x")

        self.propriedade = Propriedade.objects.create(
            nome="Fazenda Horizonte",
            municipio="Ivaiporã",
            uf="PR",
            area_hectares=Decimal("300.00"),
        )
        self.outra_propriedade = Propriedade.objects.create(
            nome="Fazenda Externa",
            municipio="Arapuã",
            uf="PR",
            area_hectares=Decimal("120.00"),
        )
        AcessoPropriedade.objects.create(
            propriedade=self.propriedade,
            usuario=self.admin,
            papel=AcessoPropriedade.Papel.ADMINISTRADOR,
        )
        AcessoPropriedade.objects.create(
            propriedade=self.propriedade,
            usuario=self.operador,
            papel=AcessoPropriedade.Papel.OPERADOR,
        )
        AcessoPropriedade.objects.create(
            propriedade=self.propriedade,
            usuario=self.leitura,
            papel=AcessoPropriedade.Papel.LEITURA,
        )
        AcessoPropriedade.objects.create(
            propriedade=self.outra_propriedade,
            usuario=self.externo,
            papel=AcessoPropriedade.Papel.ADMINISTRADOR,
        )

        self.cultura = Cultura.objects.create(nome="Soja", codigo="soja")
        self.safra = Safra.objects.create(nome="2026/2027")
        self.cadpro = CadPro.objects.create(
            propriedade=self.propriedade,
            codigo="CAD-001",
            titular="Produtor Principal",
        )
        self.cadpro_externo = CadPro.objects.create(
            propriedade=self.outra_propriedade,
            codigo="CAD-EXT",
            titular="Outro Produtor",
        )
        AcessoCadPro.objects.create(cadpro=self.cadpro, usuario=self.operador)
        AcessoCadPro.objects.create(cadpro=self.cadpro, usuario=self.leitura)

        self.silo = LocalEstoque.objects.create(
            nome="Silo Central",
            propriedade=self.propriedade,
        )
        self.silo_destino = LocalEstoque.objects.create(
            nome="Silo Secundário",
            propriedade=self.propriedade,
        )
        self.comprador = ParceiroFinanceiro.objects.create(
            nome="Cooperativa Compradora",
            tipo=ParceiroFinanceiro.Tipo.CLIENTE,
        )

    def criar_recebimento(self, quantidade="6000.000"):
        return RecebimentoProducao.objects.create(
            propriedade=self.propriedade,
            cadpro=self.cadpro,
            cultura=self.cultura,
            safra=self.safra,
            local_armazenagem=self.silo,
            peso_bruto_kg=Decimal("16000.000"),
            tara_kg=Decimal("10000.000"),
            peso_liquido_kg=Decimal(quantidade),
            umidade_percentual=Decimal("13.50"),
            impureza_percentual=Decimal("1.00"),
            defeitos_percentual=Decimal("0.50"),
            criado_por=self.operador,
        )

    def test_administrador_enxerga_todos_cadpros_da_propriedade(self):
        self.assertEqual(list(cadpros_visiveis(self.admin).values_list("id", flat=True)), [self.cadpro.id])
        self.assertFalse(
            cadpros_visiveis(self.operador).filter(pk=self.cadpro_externo.pk).exists()
        )

    def test_confirmacao_recebimento_credita_estoque_e_audita(self):
        recebimento = confirmar_recebimento(
            self.criar_recebimento(),
            usuario=self.operador,
        )
        saldo = SaldoGraos.objects.get(
            cadpro=self.cadpro,
            local_armazenagem=self.silo,
        )

        self.assertEqual(recebimento.status, RecebimentoProducao.Status.CONFIRMADO)
        self.assertEqual(recebimento.quantidade_sacas, Decimal("100.000"))
        self.assertEqual(saldo.quantidade_kg, Decimal("6000.000"))
        self.assertTrue(
            AuditoriaProducao.objects.filter(
                acao="recebimento_confirmado",
                entidade_id=recebimento.pk,
            ).exists()
        )

    def test_transferencia_move_saldo_sem_duplicar_estoque(self):
        confirmar_recebimento(self.criar_recebimento(), usuario=self.operador)
        registrar_movimentacao(
            usuario=self.operador,
            tipo=MovimentacaoGraos.Tipo.TRANSFERENCIA,
            propriedade=self.propriedade,
            cadpro=self.cadpro,
            cultura=self.cultura,
            safra=self.safra,
            quantidade_kg=Decimal("1500.000"),
            local_origem=self.silo,
            local_destino=self.silo_destino,
            motivo="Transferência operacional",
        )

        origem = SaldoGraos.objects.get(
            cadpro=self.cadpro,
            local_armazenagem=self.silo,
        )
        destino = SaldoGraos.objects.get(
            cadpro=self.cadpro,
            local_armazenagem=self.silo_destino,
        )
        self.assertEqual(origem.quantidade_kg, Decimal("4500.000"))
        self.assertEqual(destino.quantidade_kg, Decimal("1500.000"))
        self.assertEqual(
            origem.quantidade_kg + destino.quantidade_kg,
            Decimal("6000.000"),
        )

    def test_saida_acima_do_saldo_e_bloqueada(self):
        confirmar_recebimento(self.criar_recebimento(), usuario=self.operador)
        with self.assertRaises(ProducaoError):
            registrar_movimentacao(
                usuario=self.operador,
                tipo=MovimentacaoGraos.Tipo.SAIDA,
                propriedade=self.propriedade,
                cadpro=self.cadpro,
                cultura=self.cultura,
                safra=self.safra,
                quantidade_kg=Decimal("6000.001"),
                local_origem=self.silo,
            )
        self.assertEqual(
            SaldoGraos.objects.get(
                cadpro=self.cadpro,
                local_armazenagem=self.silo,
            ).quantidade_kg,
            Decimal("6000.000"),
        )

    def test_embarque_baixa_saldo_e_cria_conta_receber(self):
        confirmar_recebimento(self.criar_recebimento(), usuario=self.operador)
        embarque = EmbarqueProducao.objects.create(
            data=timezone.now(),
            propriedade=self.propriedade,
            cadpro=self.cadpro,
            cultura=self.cultura,
            safra=self.safra,
            local_armazenagem=self.silo,
            comprador=self.comprador,
            romaneio="ROM-001",
            quantidade_kg=Decimal("3000.000"),
            preco_saca=Decimal("120.00"),
            criado_por=self.operador,
        )

        embarque = confirmar_embarque(embarque, usuario=self.operador)
        saldo = SaldoGraos.objects.get(
            cadpro=self.cadpro,
            local_armazenagem=self.silo,
        )
        self.assertEqual(embarque.status, EmbarqueProducao.Status.CONFIRMADO)
        self.assertEqual(embarque.quantidade_sacas, Decimal("50.000"))
        self.assertEqual(embarque.valor_total, Decimal("6000.00"))
        self.assertEqual(saldo.quantidade_kg, Decimal("3000.000"))
        self.assertEqual(
            embarque.lancamento_financeiro.tipo,
            LancamentoFinanceiro.Tipo.RECEBER,
        )
        self.assertEqual(
            embarque.lancamento_financeiro.valor,
            Decimal("6000.00"),
        )

    def test_recurso_de_outro_cadpro_retorna_404(self):
        client = APIClient()
        client.force_authenticate(self.operador)
        response = client.get(f"/api/producao/cadpros/{self.cadpro_externo.pk}/")
        self.assertEqual(response.status_code, 404)

    def test_somente_leitura_nao_cria_recebimento(self):
        client = APIClient()
        client.force_authenticate(self.leitura)
        response = client.post(
            "/api/producao/recebimentos/",
            {
                "propriedade": self.propriedade.pk,
                "cadpro": self.cadpro.pk,
                "cultura": self.cultura.pk,
                "safra": self.safra.pk,
                "local_armazenagem": self.silo.pk,
                "peso_bruto_kg": "16000.000",
                "tara_kg": "10000.000",
                "peso_liquido_kg": "6000.000",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)

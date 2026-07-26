from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase

from apps.estoque.models import LocalEstoque
from apps.financeiro.models import LancamentoFinanceiro, ParceiroFinanceiro
from apps.propriedades.models import AcessoPropriedade, Propriedade
from apps.talhoes.models import Talhao

from .grain_enterprise_models import (
    AuditoriaCadPro,
    ConfiguracaoCultura,
    NotaFiscalProducao,
    TransferenciaGraos,
)
from .grain_enterprise_services import (
    confirmar_embarque_seguro,
    confirmar_recebimento_seguro,
    confirmar_transferencia,
    estornar_embarque_seguro,
)
from .grain_models import (
    AcessoCadPro,
    CadPro,
    ContratoProducao,
    Cultura,
    EmbarqueProducao,
    RecebimentoProducao,
    Safra,
    SaldoGraos,
)
from .grain_services import ProducaoError


@override_settings(PROPERTY_ACCESS_LEGACY_TEST_MODE=False)
class GestaoIntegradaEnterpriseTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.gestor = user_model.objects.create_user(username="gestor-enterprise", password="teste")
        self.operador = user_model.objects.create_user(username="operador-enterprise", password="teste")
        self.leitor = user_model.objects.create_user(username="leitor-enterprise", password="teste")
        self.externo = user_model.objects.create_user(username="externo-enterprise", password="teste")

        self.origem = Propriedade.objects.create(
            nome="Fazenda Origem",
            municipio="Ivaiporã",
            uf="PR",
            area_hectares="100.00",
        )
        self.destino = Propriedade.objects.create(
            nome="Fazenda Destino",
            municipio="Arapuã",
            uf="PR",
            area_hectares="80.00",
        )
        for propriedade in (self.origem, self.destino):
            AcessoPropriedade.objects.create(
                propriedade=propriedade,
                usuario=self.gestor,
                papel=AcessoPropriedade.Papel.GESTOR,
            )
        AcessoPropriedade.objects.create(
            propriedade=self.origem,
            usuario=self.operador,
            papel=AcessoPropriedade.Papel.OPERADOR,
        )
        AcessoPropriedade.objects.create(
            propriedade=self.origem,
            usuario=self.leitor,
            papel=AcessoPropriedade.Papel.LEITURA,
        )
        AcessoPropriedade.objects.create(
            propriedade=self.destino,
            usuario=self.externo,
            papel=AcessoPropriedade.Papel.GESTOR,
        )

        self.cad_origem = CadPro.objects.create(
            propriedade=self.origem,
            codigo="CAD-ORIGEM",
            titular="Produtor Origem",
        )
        self.cad_destino = CadPro.objects.create(
            propriedade=self.destino,
            codigo="CAD-DESTINO",
            titular="Produtor Destino",
        )
        for cadpro in (self.cad_origem, self.cad_destino):
            AcessoCadPro.objects.create(cadpro=cadpro, usuario=self.gestor)
        AcessoCadPro.objects.create(cadpro=self.cad_origem, usuario=self.operador)
        AcessoCadPro.objects.create(cadpro=self.cad_origem, usuario=self.leitor)
        AcessoCadPro.objects.create(cadpro=self.cad_destino, usuario=self.externo)

        self.cultura = Cultura.objects.create(nome="Soja Enterprise", codigo="soja-enterprise", peso_saca_kg="60")
        ConfiguracaoCultura.objects.create(
            cultura=self.cultura,
            umidade_alerta_percentual="14.00",
            estoque_minimo_kg="1000.000",
        )
        self.safra = Safra.objects.create(nome="2026/2027 Enterprise")
        self.local_origem = LocalEstoque.objects.create(nome="Silo Origem", propriedade=self.origem)
        self.local_destino = LocalEstoque.objects.create(nome="Silo Destino", propriedade=self.destino)
        self.talhao_origem = Talhao.objects.create(
            propriedade=self.origem,
            nome="Talhão Origem",
            area_hectares="20.00",
            cultura_atual="Soja",
            safra="2026/2027 Enterprise",
            produtividade_esperada="60.00",
        )
        self.talhao_destino = Talhao.objects.create(
            propriedade=self.destino,
            nome="Talhão Destino",
            area_hectares="10.00",
            cultura_atual="Soja",
            safra="2026/2027 Enterprise",
        )
        self.comprador = ParceiroFinanceiro.objects.create(
            nome="Comprador Enterprise",
            tipo=ParceiroFinanceiro.Tipo.CLIENTE,
        )
        self.contrato = ContratoProducao.objects.create(
            propriedade=self.origem,
            cadpro=self.cad_origem,
            cultura=self.cultura,
            safra=self.safra,
            comprador=self.comprador,
            numero="CONT-001",
            quantidade_kg="6000.000",
            preco_saca="125.00",
        )

    def criar_recebimento(self, quantidade="6000.000"):
        return RecebimentoProducao.objects.create(
            propriedade=self.origem,
            cadpro=self.cad_origem,
            talhao=self.talhao_origem,
            cultura=self.cultura,
            safra=self.safra,
            local_armazenagem=self.local_origem,
            peso_bruto_kg="10000.000",
            tara_kg="3000.000",
            peso_liquido_kg=quantidade,
            umidade_percentual="15.500",
            impureza_percentual="1.000",
            defeitos_percentual="0.500",
            criado_por=self.gestor,
        )

    def test_transferencia_entre_propriedades_preserva_total_e_auditoria(self):
        confirmar_recebimento_seguro(self.criar_recebimento(), usuario=self.gestor)
        transferencia = TransferenciaGraos.objects.create(
            propriedade_origem=self.origem,
            cadpro_origem=self.cad_origem,
            talhao_origem=self.talhao_origem,
            local_origem=self.local_origem,
            propriedade_destino=self.destino,
            cadpro_destino=self.cad_destino,
            talhao_destino=self.talhao_destino,
            local_destino=self.local_destino,
            cultura=self.cultura,
            safra=self.safra,
            quantidade_kg="1500.000",
            criado_por=self.gestor,
        )
        transferencia = confirmar_transferencia(transferencia, usuario=self.gestor)
        origem = SaldoGraos.objects.get(cadpro=self.cad_origem, local_armazenagem=self.local_origem)
        destino = SaldoGraos.objects.get(cadpro=self.cad_destino, local_armazenagem=self.local_destino)
        self.assertEqual(transferencia.status, TransferenciaGraos.Status.CONFIRMADA)
        self.assertEqual(origem.quantidade_kg, Decimal("4500.000"))
        self.assertEqual(destino.quantidade_kg, Decimal("1500.000"))
        self.assertEqual(origem.quantidade_kg + destino.quantidade_kg, Decimal("6000.000"))
        self.assertTrue(
            AuditoriaCadPro.objects.filter(
                auditoria__acao="transferencia_confirmada",
                cadpro=self.cad_origem,
            ).exists()
        )

    def test_transferencia_cruzada_exige_acesso_aos_dois_cadpros(self):
        confirmar_recebimento_seguro(self.criar_recebimento(), usuario=self.gestor)
        transferencia = TransferenciaGraos.objects.create(
            propriedade_origem=self.origem,
            cadpro_origem=self.cad_origem,
            local_origem=self.local_origem,
            propriedade_destino=self.destino,
            cadpro_destino=self.cad_destino,
            local_destino=self.local_destino,
            cultura=self.cultura,
            safra=self.safra,
            quantidade_kg="100.000",
            criado_por=self.gestor,
        )
        with self.assertRaises(Exception):
            confirmar_transferencia(transferencia, usuario=self.externo)
        self.assertEqual(
            SaldoGraos.objects.get(cadpro=self.cad_origem).quantidade_kg,
            Decimal("6000.000"),
        )

    def test_operador_nao_confirma_embarque_financeiro(self):
        confirmar_recebimento_seguro(self.criar_recebimento(), usuario=self.gestor)
        embarque = EmbarqueProducao.objects.create(
            propriedade=self.origem,
            cadpro=self.cad_origem,
            cultura=self.cultura,
            safra=self.safra,
            local_armazenagem=self.local_origem,
            comprador=self.comprador,
            contrato=self.contrato,
            romaneio="ROM-ENTERPRISE-01",
            nota_produtor="NF-001",
            quantidade_kg="3000.000",
            preco_saca="125.00",
            criado_por=self.gestor,
        )
        with self.assertRaises(Exception):
            confirmar_embarque_seguro(embarque, usuario=self.operador)
        embarque = confirmar_embarque_seguro(embarque, usuario=self.gestor)
        self.assertEqual(embarque.status, EmbarqueProducao.Status.CONFIRMADO)
        self.assertTrue(
            NotaFiscalProducao.objects.filter(
                embarque=embarque,
                numero="NF-001",
            ).exists()
        )

    def test_embarque_sem_contrato_ou_nota_nao_confirma(self):
        confirmar_recebimento_seguro(self.criar_recebimento(), usuario=self.gestor)
        embarque = EmbarqueProducao.objects.create(
            propriedade=self.origem,
            cadpro=self.cad_origem,
            cultura=self.cultura,
            safra=self.safra,
            local_armazenagem=self.local_origem,
            comprador=self.comprador,
            romaneio="ROM-SEM-DOC",
            quantidade_kg="1000.000",
            preco_saca="120.00",
            criado_por=self.gestor,
        )
        with self.assertRaises(ProducaoError):
            confirmar_embarque_seguro(embarque, usuario=self.gestor)

    def test_estorno_bloqueado_apos_liquidacao_financeira(self):
        confirmar_recebimento_seguro(self.criar_recebimento(), usuario=self.gestor)
        embarque = EmbarqueProducao.objects.create(
            propriedade=self.origem,
            cadpro=self.cad_origem,
            cultura=self.cultura,
            safra=self.safra,
            local_armazenagem=self.local_origem,
            comprador=self.comprador,
            contrato=self.contrato,
            romaneio="ROM-LIQUIDADO",
            nota_empresa="NF-E-001",
            quantidade_kg="1000.000",
            preco_saca="125.00",
            criado_por=self.gestor,
        )
        embarque = confirmar_embarque_seguro(embarque, usuario=self.gestor)
        lancamento = embarque.lancamento_financeiro
        lancamento.status = LancamentoFinanceiro.Status.LIQUIDADO
        lancamento.data_liquidacao = lancamento.data_emissao
        lancamento.save(update_fields=("status", "data_liquidacao", "atualizado_em"))
        with self.assertRaises(ProducaoError):
            estornar_embarque_seguro(embarque, usuario=self.gestor, motivo="Teste")

    def test_dashboard_e_relatorios_respeitam_cadpro(self):
        confirmar_recebimento_seguro(self.criar_recebimento(), usuario=self.gestor)
        self.client.force_authenticate(self.leitor)
        dashboard = self.client.get("/api/producao/dashboard-integrado/")
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(
            Decimal(str(dashboard.data["producao"]["peso_liquido_kg"])),
            Decimal("6000.000"),
        )
        report = self.client.get("/api/producao/relatorios-integrados/?tipo=estoque")
        self.assertEqual(report.status_code, 200)
        self.assertEqual(report.data["count"], 1)

    def test_usuario_externo_nao_acessa_auditoria_de_outro_cadpro(self):
        confirmar_recebimento_seguro(self.criar_recebimento(), usuario=self.gestor)
        self.client.force_authenticate(self.externo)
        response = self.client.get("/api/producao/auditoria/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

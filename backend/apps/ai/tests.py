from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.financeiro.models import CategoriaFinanceira, LancamentoFinanceiro
from apps.graos.models import ArmazemGraos, LoteGraos, MovimentacaoGraos
from apps.graos.services import registrar_movimentacao
from apps.propriedades.models import Propriedade

from .services import gerar_insights


class InsightsBase:
    def dados(self):
        self.usuario = get_user_model().objects.create_user("insights", password="x")
        self.propriedade = Propriedade.objects.create(
            nome="Fazenda Insights", municipio="Sorriso", uf="MT", area_hectares="100"
        )


class InsightsServiceTests(InsightsBase, TestCase):
    def setUp(self): self.dados()

    def test_retorna_informativo_sem_pendencias(self):
        dados = gerar_insights(propriedade=self.propriedade.id)
        self.assertEqual(dados["metodo"], "regras_explicaveis_v1")
        self.assertEqual(dados["insights"][0]["codigo"], "sem_alertas")

    def test_detecta_financeiro_atrasado_com_evidencia(self):
        categoria = CategoriaFinanceira.objects.create(nome="Despesa IA", aplicacao="despesa")
        LancamentoFinanceiro.objects.create(
            tipo="pagar", descricao="Conta", valor="100", categoria=categoria,
            propriedade=self.propriedade,
            data_vencimento=timezone.localdate() - timedelta(days=1),
        )
        insight = gerar_insights(propriedade=self.propriedade.id)["insights"][0]
        self.assertEqual(insight["codigo"], "financeiro_atrasado")
        self.assertIn("1 lançamento", insight["evidencia"])

    def test_integra_saldo_ocupacao_e_lote_inativo_de_graos(self):
        armazem = ArmazemGraos.objects.create(
            propriedade=self.propriedade,
            nome="Silo IA",
            capacidade_kg="1000",
        )
        lote = LoteGraos.objects.create(
            armazem=armazem,
            codigo="SOJA-IA",
            cultura="Soja",
            safra="2026/2027",
        )
        registrar_movimentacao(
            usuario=self.usuario,
            tipo=MovimentacaoGraos.Tipo.ENTRADA,
            lote=lote,
            quantidade_kg="900",
            data_movimento=timezone.localdate(),
        )
        lote.ativo = False
        lote.save(update_fields=("ativo",))

        dados = gerar_insights(
            propriedade=self.propriedade.id,
            safra="2026/2027",
        )
        por_codigo = {item["codigo"]: item for item in dados["insights"]}

        self.assertIn("graos_saldo_disponivel", por_codigo)
        self.assertIn(
            "900.000 kg",
            por_codigo["graos_saldo_disponivel"]["evidencia"],
        )
        self.assertIn("graos_lotes_inativos_com_saldo", por_codigo)
        self.assertIn(f"graos_ocupacao_armazem_{armazem.id}", por_codigo)

    def test_graos_respeitam_filtros_de_propriedade_e_safra(self):
        outra = Propriedade.objects.create(
            nome="Fazenda externa",
            municipio="Sinop",
            uf="MT",
            area_hectares="200",
        )
        armazem = ArmazemGraos.objects.create(
            propriedade=outra,
            nome="Silo externo",
            capacidade_kg="1000",
        )
        lote = LoteGraos.objects.create(
            armazem=armazem,
            codigo="MILHO-EXTERNO",
            cultura="Milho",
            safra="2025/2026",
        )
        registrar_movimentacao(
            usuario=self.usuario,
            tipo=MovimentacaoGraos.Tipo.ENTRADA,
            lote=lote,
            quantidade_kg="950",
            data_movimento=timezone.localdate(),
        )

        dados = gerar_insights(
            propriedade=self.propriedade.id,
            safra="2026/2027",
        )
        codigos = [item["codigo"] for item in dados["insights"]]

        self.assertEqual(codigos, ["sem_alertas"])

    def test_saldo_de_graos_respeita_filtro_de_safra(self):
        armazem = ArmazemGraos.objects.create(
            propriedade=self.propriedade,
            nome="Silo safra anterior",
            capacidade_kg="1000",
        )
        lote = LoteGraos.objects.create(
            armazem=armazem,
            codigo="SOJA-ANTERIOR",
            cultura="Soja",
            safra="2025/2026",
        )
        registrar_movimentacao(
            usuario=self.usuario,
            tipo=MovimentacaoGraos.Tipo.ENTRADA,
            lote=lote,
            quantidade_kg="100",
            data_movimento=timezone.localdate(),
        )

        dados = gerar_insights(
            propriedade=self.propriedade.id,
            safra="2026/2027",
        )

        self.assertEqual(
            [item["codigo"] for item in dados["insights"]],
            ["sem_alertas"],
        )

    def test_ocupacao_considera_saldos_de_todas_as_safras(self):
        armazem = ArmazemGraos.objects.create(
            propriedade=self.propriedade,
            nome="Silo compartilhado",
            capacidade_kg="1000",
        )
        lote_atual = LoteGraos.objects.create(
            armazem=armazem,
            codigo="SOJA-ATUAL",
            cultura="Soja",
            safra="2026/2027",
        )
        lote_anterior = LoteGraos.objects.create(
            armazem=armazem,
            codigo="SOJA-ANTERIOR",
            cultura="Soja",
            safra="2025/2026",
        )
        for lote, quantidade in ((lote_atual, "100"), (lote_anterior, "800")):
            registrar_movimentacao(
                usuario=self.usuario,
                tipo=MovimentacaoGraos.Tipo.ENTRADA,
                lote=lote,
                quantidade_kg=quantidade,
                data_movimento=timezone.localdate(),
            )

        dados = gerar_insights(
            propriedade=self.propriedade.id,
            safra="2026/2027",
        )
        por_codigo = {item["codigo"]: item for item in dados["insights"]}

        self.assertIn(f"graos_ocupacao_armazem_{armazem.id}", por_codigo)
        self.assertIn(
            "100.000 kg",
            por_codigo["graos_saldo_disponivel"]["evidencia"],
        )
        self.assertIn(
            "90.00%",
            por_codigo[f"graos_ocupacao_armazem_{armazem.id}"]["evidencia"],
        )

    def test_ocupacao_abaixo_do_limite_nao_gera_alerta(self):
        armazem = ArmazemGraos.objects.create(
            propriedade=self.propriedade,
            nome="Silo abaixo do limite",
            capacidade_kg="1000",
        )
        lote = LoteGraos.objects.create(
            armazem=armazem,
            codigo="MILHO-899",
            cultura="Milho",
            safra="2026/2027",
        )
        registrar_movimentacao(
            usuario=self.usuario,
            tipo=MovimentacaoGraos.Tipo.ENTRADA,
            lote=lote,
            quantidade_kg="899.999",
            data_movimento=timezone.localdate(),
        )

        codigos = {
            item["codigo"]
            for item in gerar_insights(propriedade=self.propriedade.id)["insights"]
        }

        self.assertNotIn(f"graos_ocupacao_armazem_{armazem.id}", codigos)

    def test_saldo_zero_nao_gera_insight_de_graos(self):
        armazem = ArmazemGraos.objects.create(
            propriedade=self.propriedade,
            nome="Silo zerado",
            capacidade_kg="1000",
        )
        lote = LoteGraos.objects.create(
            armazem=armazem,
            codigo="TRIGO-ZERO",
            cultura="Trigo",
            safra="2026/2027",
        )
        for tipo in (MovimentacaoGraos.Tipo.ENTRADA, MovimentacaoGraos.Tipo.SAIDA):
            registrar_movimentacao(
                usuario=self.usuario,
                tipo=tipo,
                lote=lote,
                quantidade_kg="100",
                data_movimento=timezone.localdate(),
            )

        dados = gerar_insights(propriedade=self.propriedade.id)

        self.assertEqual(
            [item["codigo"] for item in dados["insights"]],
            ["sem_alertas"],
        )

    def test_saldo_negativo_alerta_sem_reduzir_ocupacao(self):
        armazem = ArmazemGraos.objects.create(
            propriedade=self.propriedade,
            nome="Silo com inconsistência",
            capacidade_kg="1000",
        )
        lote_positivo = LoteGraos.objects.create(
            armazem=armazem,
            codigo="SOJA-POSITIVA",
            cultura="Soja",
            safra="2026/2027",
        )
        lote_negativo = LoteGraos.objects.create(
            armazem=armazem,
            codigo="SOJA-NEGATIVA",
            cultura="Soja",
            safra="2025/2026",
        )
        registrar_movimentacao(
            usuario=self.usuario,
            tipo=MovimentacaoGraos.Tipo.ENTRADA,
            lote=lote_positivo,
            quantidade_kg="950",
            data_movimento=timezone.localdate(),
        )
        MovimentacaoGraos.objects.create(
            criado_por=self.usuario,
            tipo=MovimentacaoGraos.Tipo.SAIDA,
            lote=lote_negativo,
            quantidade_kg="200",
            data_movimento=timezone.localdate(),
        )

        dados = gerar_insights(
            propriedade=self.propriedade.id,
            safra="2026/2027",
        )
        por_codigo = {item["codigo"]: item for item in dados["insights"]}

        self.assertIn("graos_saldos_inconsistentes", por_codigo)
        self.assertIn(
            "déficit total de 200.000 kg",
            por_codigo["graos_saldos_inconsistentes"]["evidencia"],
        )
        self.assertIn(f"graos_ocupacao_armazem_{armazem.id}", por_codigo)
        self.assertIn(
            "95.00%",
            por_codigo[f"graos_ocupacao_armazem_{armazem.id}"]["evidencia"],
        )


class InsightsApiTests(InsightsBase, APITestCase):
    def setUp(self):
        self.dados()
        self.client.force_authenticate(self.usuario)

    def test_exige_autenticacao(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/ai/insights/").status_code, 401)

    def test_resposta_tem_aviso_e_metodo(self):
        resposta = self.client.get(f"/api/ai/insights/?propriedade={self.propriedade.id}")
        self.assertEqual(resposta.status_code, 200)
        self.assertIn("Não substitui", resposta.data["aviso"])

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.financeiro.models import CategoriaFinanceira, LancamentoFinanceiro
from apps.maquinas.models import Maquina, ManutencaoMaquina
from apps.producao.models import OperacaoAgricola
from apps.propriedades.models import Propriedade
from apps.talhoes.models import Talhao

from .services import dashboard_gerencial


class DashboardBase:
    def dados(self):
        self.usuario = get_user_model().objects.create_user("relatorios", password="x")
        self.propriedade = Propriedade.objects.create(
            nome="Fazenda Relatório", municipio="Sorriso", uf="MT", area_hectares="100"
        )
        self.outra = Propriedade.objects.create(
            nome="Outra Fazenda", municipio="Lucas", uf="MT", area_hectares="50"
        )
        self.talhao = Talhao.objects.create(
            propriedade=self.propriedade, nome="Talhão R", area_hectares="40", safra="2026/2027"
        )
        self.operacao = OperacaoAgricola.objects.create(
            talhao=self.talhao, tipo="plantio", descricao="Plantio", data_planejada=timezone.localdate(),
            area_hectares="40", custo_estimado="1000", custo_realizado="900",
            status="concluida", data_inicio=timezone.localdate(), data_conclusao=timezone.localdate(),
            criado_por=self.usuario,
        )
        categoria = CategoriaFinanceira.objects.create(nome="Venda", aplicacao="receita")
        LancamentoFinanceiro.objects.create(
            tipo="receber", descricao="Venda", valor="2000", valor_liquidado="2000",
            categoria=categoria, propriedade=self.propriedade, safra="2026/2027",
            data_vencimento=timezone.localdate(), data_liquidacao=timezone.localdate(),
            status="liquidado",
        )
        self.maquina = Maquina.objects.create(
            identificacao="REL-1", tipo="trator", propriedade=self.propriedade
        )
        ManutencaoMaquina.objects.create(
            maquina=self.maquina, descricao="Revisão", data_prevista=timezone.localdate()
        )


class DashboardServiceTests(DashboardBase, TestCase):
    def setUp(self): self.dados()

    def test_consolida_indicadores(self):
        dados = dashboard_gerencial()
        self.assertEqual(dados["estrutura"]["propriedades"], 2)
        self.assertEqual(dados["operacoes"]["concluidas"], 1)
        self.assertEqual(dados["financeiro"]["entradas_realizadas"], 2000)
        self.assertEqual(dados["maquinas"]["manutencoes_pendentes"], 1)
        self.assertEqual(len(dados["fluxo_mensal"]), 1)

    def test_filtra_propriedade_e_safra(self):
        dados = dashboard_gerencial(propriedade=self.outra.id, safra="2026/2027")
        self.assertEqual(dados["estrutura"]["talhoes"], 0)
        self.assertEqual(dados["operacoes"]["total"], 0)
        self.assertEqual(dados["financeiro"]["entradas_realizadas"], 0)


class DashboardApiTests(DashboardBase, APITestCase):
    def setUp(self):
        self.dados()
        self.client.force_authenticate(self.usuario)

    def test_exige_autenticacao(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/relatorios/dashboard/").status_code, 401)

    def test_retorna_dashboard_filtrado(self):
        resposta = self.client.get(
            f"/api/relatorios/dashboard/?propriedade={self.propriedade.id}&safra=2026/2027"
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.data["estrutura"]["talhoes"], 1)
        self.assertEqual(resposta.data["operacoes"]["custo_realizado"], 900)

    def test_centraliza_relatorios_de_todos_os_modulos(self):
        esperados = {
            "estrutura": ("propriedade_nome", "Fazenda Relatório"),
            "financeiro": ("descricao", "Venda"),
            "operacoes_agricolas": ("descricao", "Plantio"),
            "maquinas": ("identificacao", "REL-1"),
        }
        for secao, (campo, valor) in esperados.items():
            with self.subTest(secao=secao):
                resposta = self.client.get(
                    "/api/relatorios/operacionais/",
                    {"secao": secao, "propriedade": self.propriedade.pk},
                )
                self.assertEqual(resposta.status_code, 200)
                self.assertEqual(resposta.data["secao"], secao)
                self.assertEqual(resposta.data["dados"]["resultados"][0][campo], valor)

        for secao in ("estoque_insumos", "clima", "mercado", "importacoes"):
            with self.subTest(secao=secao):
                resposta = self.client.get(
                    "/api/relatorios/operacionais/", {"secao": secao}
                )
                self.assertEqual(resposta.status_code, 200)
                self.assertEqual(resposta.data["secao"], secao)


class CustosMaquinasAuditoriaTests(DashboardBase, TestCase):
    def setUp(self): self.dados()
    def test_componentes_periodo_horas_e_manutencao(self):
        from decimal import Decimal
        from datetime import timedelta
        from apps.maquinas.models import UsoMaquina, AbastecimentoMaquina
        from .selectors import _maquinas
        hoje=timezone.localdate()
        UsoMaquina.objects.create(maquina=self.maquina,operacao=self.operacao,data=hoje,horimetro_inicial="0",horimetro_final="10")
        AbastecimentoMaquina.objects.create(maquina=self.maquina,data=hoje,litros="20",valor_total="100",horimetro="10")
        ManutencaoMaquina.objects.create(maquina=self.maquina,descricao="Realizada",data_prevista=hoje-timedelta(days=40),data_conclusao=hoje,status="concluida",custo="200")
        ManutencaoMaquina.objects.create(maquina=self.maquina,descricao="Cancelada",data_prevista=hoje,status="cancelada",custo="999")
        self.maquina.horimetro_atual=Decimal("10");self.maquina.save()
        ManutencaoMaquina.objects.create(maquina=self.maquina,descricao="Próxima",data_prevista=hoje+timedelta(days=20),horimetro_previsto="50")
        row=_maquinas({"propriedade":self.propriedade.pk,"data_inicio":hoje,"data_fim":hoje})[0]
        self.assertEqual(Decimal(row["custo_por_hora_registrada"]),Decimal("30"))
        self.assertEqual(Decimal(row["litros_por_hora_registrada"]),Decimal("2"))
        self.assertEqual(Decimal(row["horas_ate_manutencao"]),Decimal("40"))
        self.assertIsNone(_maquinas({"propriedade":self.propriedade.pk,"data_inicio":hoje+timedelta(days=1)})[0]["custo_por_hora_registrada"])

    def test_paginacao_maquinas_no_banco_sem_carregar_outros_usos(self):
        from .selectors import selecionar_relatorio_operacional
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        for i in range(30): Maquina.objects.create(identificacao=f"PAG-{i:02}",tipo="trator",propriedade=self.propriedade)
        with CaptureQueriesContext(connection) as ctx:
            r=selecionar_relatorio_operacional(secao="maquinas",pagina=2,por_pagina=5)
        self.assertEqual(r["dados"]["total"],31)
        self.assertEqual(len(r["dados"]["resultados"]),5)
        self.assertTrue(any("LIMIT 5 OFFSET 5" in q["sql"] for q in ctx.captured_queries))

    def test_comparacao_operacao_nao_inventa_area_quantidade_custo(self):
        from .selectors import _operacoes_agricolas
        from decimal import Decimal
        row=_operacoes_agricolas({"propriedade":self.propriedade.pk})[0]
        self.assertEqual(Decimal(row["comparacao"]["custo_diferenca"]),Decimal("-100"))
        self.assertEqual(row["comparacao"]["duracao_realizada_dias"],0)
        self.assertEqual(row["comparacao"]["insumos"],[])
        self.operacao.custo_realizado=None;self.operacao.save()
        self.assertIsNone(_operacoes_agricolas({"propriedade":self.propriedade.pk})[0]["comparacao"]["custo_diferenca"])

    def test_consumo_rastreia_baixa_sem_somar_unidades_ou_custo_ausente(self):
        from .selectors import _operacoes_agricolas
        from apps.producao.models import InsumoOperacao
        from apps.estoque.models import ProdutoEstoque,LoteEstoque,MovimentacaoEstoque
        from decimal import Decimal
        for unidade in ["kg","l"]:
            produto=ProdutoEstoque.objects.create(nome=f"Produto-{unidade}",categoria="insumo",unidade=unidade)
            lote=LoteEstoque.objects.create(produto=produto,codigo="AUD")
            movimento=MovimentacaoEstoque.objects.create(tipo="saida",lote=lote,quantidade="12",custo_unitario="2" if unidade=="kg" else None,documento_fiscal="NF-AUD",criado_por=self.usuario)
            InsumoOperacao.objects.create(operacao=self.operacao,lote=lote,quantidade_planejada="10",quantidade_utilizada="11",movimentacao_estoque=movimento)
        r=_operacoes_agricolas({"propriedade":self.propriedade.pk})[0]["comparacao"]
        por_unidade={i["unidade"]:i for i in r["insumos"]}
        self.assertEqual(Decimal(por_unidade["kg"]["utilizada"]),Decimal("12"))
        self.assertEqual(Decimal(por_unidade["kg"]["diferenca"]),Decimal("2"))
        self.assertEqual(Decimal(por_unidade["kg"]["custo_registrado"]),Decimal("24"))
        self.assertIsNone(por_unidade["l"]["custo_registrado"])
        self.assertEqual(por_unidade["kg"]["documento"],"NF-AUD")

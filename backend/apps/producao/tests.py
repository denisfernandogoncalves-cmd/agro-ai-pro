from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.estoque.models import LocalEstoque, LoteEstoque, ProdutoEstoque
from apps.estoque.services import registrar_movimentacao, saldo_lote
from apps.propriedades.models import Propriedade
from apps.talhoes.models import Talhao

from .models import InsumoOperacao, OperacaoAgricola
from .services import (
    TransicaoOperacaoError,
    cancelar_operacao,
    concluir_operacao,
    iniciar_operacao,
)


class OperacaoBase:
    def criar_dados(self):
        self.usuario = get_user_model().objects.create_user("operador", password="x")
        self.propriedade = Propriedade.objects.create(
            nome="Fazenda Operações",
            municipio="Rio Verde",
            uf="GO",
            area_hectares="100",
        )
        self.talhao = Talhao.objects.create(
            propriedade=self.propriedade,
            nome="Talhão Sul",
            area_hectares="40",
            cultura_atual="Soja",
            safra="2026/2027",
        )
        self.produto = ProdutoEstoque.objects.create(
            nome="Fertilizante operacional",
            categoria="fertilizante",
            unidade="kg",
        )
        self.local = LocalEstoque.objects.create(
            nome="Galpão operacional",
            propriedade=self.propriedade,
        )
        self.lote = LoteEstoque.objects.create(
            produto=self.produto,
            local=self.local,
            codigo="OP-001",
        )
        registrar_movimentacao(
            usuario=self.usuario,
            tipo="entrada",
            lote=self.lote,
            quantidade="500",
            custo_unitario="3.50",
            data_movimento=timezone.localdate(),
        )
        self.operacao = OperacaoAgricola.objects.create(
            talhao=self.talhao,
            tipo="adubacao",
            descricao="Adubação de cobertura",
            data_planejada=timezone.localdate(),
            area_hectares="40",
            responsavel="Equipe de campo",
            custo_estimado="2500",
            criado_por=self.usuario,
        )


class OperacaoRegrasTests(OperacaoBase, TestCase):
    def setUp(self):
        self.criar_dados()

    def test_area_nao_pode_superar_talhao(self):
        self.operacao.area_hectares = Decimal("41")
        with self.assertRaisesMessage(ValidationError, "superar a área"):
            self.operacao.full_clean()

    def test_fluxo_iniciar_e_concluir_baixa_estoque(self):
        insumo = InsumoOperacao.objects.create(
            operacao=self.operacao,
            lote=self.lote,
            quantidade_planejada="120",
            quantidade_utilizada="110",
        )
        iniciar_operacao(self.operacao)
        concluida = concluir_operacao(
            self.operacao,
            usuario=self.usuario,
            custo_realizado="2300",
        )
        insumo.refresh_from_db()
        self.assertEqual(concluida.status, OperacaoAgricola.Status.CONCLUIDA)
        self.assertEqual(concluida.custo_realizado, Decimal("2300"))
        self.assertIsNotNone(insumo.movimentacao_estoque_id)
        self.assertEqual(saldo_lote(self.lote), Decimal("390"))

    def test_conclusao_sem_saldo_e_atomica(self):
        InsumoOperacao.objects.create(
            operacao=self.operacao,
            lote=self.lote,
            quantidade_planejada="501",
        )
        iniciar_operacao(self.operacao)
        with self.assertRaisesMessage(ValueError, "Saldo insuficiente"):
            concluir_operacao(self.operacao, usuario=self.usuario)
        self.operacao.refresh_from_db()
        self.assertEqual(self.operacao.status, OperacaoAgricola.Status.EM_EXECUCAO)
        self.assertEqual(saldo_lote(self.lote), Decimal("500"))

    def test_transicoes_invalidas_sao_bloqueadas(self):
        with self.assertRaises(TransicaoOperacaoError):
            concluir_operacao(self.operacao, usuario=self.usuario)
        cancelar_operacao(self.operacao)
        with self.assertRaises(TransicaoOperacaoError):
            iniciar_operacao(self.operacao)

    def test_insumo_nao_pode_mudar_em_operacao_concluida(self):
        insumo = InsumoOperacao.objects.create(
            operacao=self.operacao,
            lote=self.lote,
            quantidade_planejada="10",
        )
        iniciar_operacao(self.operacao)
        concluir_operacao(self.operacao, usuario=self.usuario)
        insumo.refresh_from_db()
        insumo.quantidade_utilizada = Decimal("9")
        with self.assertRaisesMessage(ValidationError, "não podem ser alterados"):
            insumo.full_clean()


class OperacaoApiTests(OperacaoBase, APITestCase):
    def setUp(self):
        self.criar_dados()
        self.client.force_authenticate(self.usuario)

    def test_autenticacao_obrigatoria(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/producao/operacoes/").status_code, 401)
        self.assertEqual(self.client.get("/api/producao/insumos/").status_code, 401)

    def test_crud_filtros_e_detalhes(self):
        resposta = self.client.post(
            "/api/producao/operacoes/",
            {
                "talhao": self.talhao.id,
                "tipo": "plantio",
                "descricao": "Plantio principal",
                "data_planejada": str(timezone.localdate() + timedelta(days=1)),
                "area_hectares": "35",
                "responsavel": "João",
                "custo_estimado": "10000",
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 201, resposta.data)
        lista = self.client.get(
            f"/api/producao/operacoes/?tipo=plantio&talhao={self.talhao.id}&search=principal"
        )
        self.assertEqual(lista.status_code, 200)
        self.assertEqual(len(lista.data), 1)
        self.assertEqual(lista.data[0]["propriedade_nome"], self.propriedade.nome)

    def test_fluxo_http_com_consumo(self):
        insumo = self.client.post(
            "/api/producao/insumos/",
            {
                "operacao": self.operacao.id,
                "lote": self.lote.id,
                "quantidade_planejada": "50",
                "quantidade_utilizada": "48",
            },
            format="json",
        )
        self.assertEqual(insumo.status_code, 201, insumo.data)
        inicio = self.client.post(
            f"/api/producao/operacoes/{self.operacao.id}/iniciar/",
            {"data_inicio": str(timezone.localdate())},
            format="json",
        )
        self.assertEqual(inicio.status_code, 200)
        conclusao = self.client.post(
            f"/api/producao/operacoes/{self.operacao.id}/concluir/",
            {
                "data_conclusao": str(timezone.localdate()),
                "custo_realizado": "2400",
            },
            format="json",
        )
        self.assertEqual(conclusao.status_code, 200, conclusao.data)
        self.assertEqual(conclusao.data["status"], "concluida")
        movimento = conclusao.data["insumos"][0]["movimentacao_estoque"]
        self.assertIsNotNone(movimento)

    def test_operacao_encerrada_nao_pode_ser_editada_ou_excluida(self):
        iniciar_operacao(self.operacao)
        concluir_operacao(self.operacao, usuario=self.usuario)
        url = f"/api/producao/operacoes/{self.operacao.id}/"
        self.assertEqual(self.client.patch(url, {"descricao": "Mudança"}).status_code, 409)
        self.assertEqual(self.client.delete(url).status_code, 409)

    def test_insumo_encerrado_nao_pode_ser_editado(self):
        insumo = InsumoOperacao.objects.create(
            operacao=self.operacao,
            lote=self.lote,
            quantidade_planejada="10",
        )
        iniciar_operacao(self.operacao)
        concluir_operacao(self.operacao, usuario=self.usuario)
        resposta = self.client.patch(
            f"/api/producao/insumos/{insumo.id}/",
            {"quantidade_utilizada": "5"},
            format="json",
        )
        self.assertEqual(resposta.status_code, 409)

    def test_cancelamento_e_transicao_repetida(self):
        resposta = self.client.post(
            f"/api/producao/operacoes/{self.operacao.id}/cancelar/",
            {},
            format="json",
        )
        self.assertEqual(resposta.status_code, 200)
        repetida = self.client.post(
            f"/api/producao/operacoes/{self.operacao.id}/cancelar/",
            {},
            format="json",
        )
        self.assertEqual(repetida.status_code, 409)

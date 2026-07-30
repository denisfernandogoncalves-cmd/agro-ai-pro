from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.propriedades.models import Propriedade
from apps.talhoes.models import Talhao

from .models import ArmazemGraos, LoteGraos, MovimentacaoGraos
from .services import (
    CapacidadeArmazemExcedidaError,
    MovimentacaoGraosConflitanteError,
    SaldoGraosInsuficienteError,
    posicao_graos,
    registrar_movimentacao,
    resumo_graos,
    saldo_armazem,
    saldo_lote,
    transferir_graos,
)


class GraosBase:
    def criar_dados(self):
        self.usuario = get_user_model().objects.create_user(
            "operador_graos",
            password="senha-teste",
        )
        self.propriedade = Propriedade.objects.create(
            nome="Fazenda Grãos",
            municipio="Sorriso",
            uf="MT",
            area_hectares="1000",
        )
        self.talhao = Talhao.objects.create(
            propriedade=self.propriedade,
            nome="Talhão 01",
            area_hectares="100",
            cultura_atual="Soja",
            safra="2026/2027",
        )
        self.armazem = ArmazemGraos.objects.create(
            propriedade=self.propriedade,
            nome="Silo principal",
            capacidade_kg="1000",
        )
        self.lote = LoteGraos.objects.create(
            armazem=self.armazem,
            talhao=self.talhao,
            codigo="SOJA-001",
            cultura="Soja",
            safra="2026/2027",
            umidade_percentual="13.50",
            impureza_percentual="1.20",
        )

    def movimentar(self, tipo, quantidade, lote=None, **dados):
        return registrar_movimentacao(
            usuario=self.usuario,
            tipo=tipo,
            lote=lote or self.lote,
            quantidade_kg=quantidade,
            data_movimento=timezone.localdate(),
            **dados,
        )


class GraosRegrasTests(GraosBase, TestCase):
    def setUp(self):
        self.criar_dados()

    def test_lote_exige_talhao_da_mesma_propriedade(self):
        outra = Propriedade.objects.create(
            nome="Outra Fazenda",
            municipio="Sinop",
            uf="MT",
            area_hectares="500",
        )
        talhao_externo = Talhao.objects.create(
            propriedade=outra,
            nome="Talhão externo",
            area_hectares="50",
        )
        self.lote.talhao = talhao_externo
        with self.assertRaisesMessage(ValidationError, "mesma propriedade"):
            self.lote.full_clean()

    def test_saldo_soma_entradas_e_subtrai_saidas(self):
        self.movimentar("entrada", "750.500")
        self.movimentar("saida", "50.250")
        self.assertEqual(saldo_lote(self.lote), Decimal("700.250"))
        self.assertEqual(saldo_armazem(self.armazem), Decimal("700.250"))

    def test_saida_sem_saldo_e_bloqueada(self):
        self.movimentar("entrada", "10")
        with self.assertRaisesMessage(
            SaldoGraosInsuficienteError,
            "Saldo insuficiente",
        ):
            self.movimentar("saida", "10.001")

    def test_entrada_acima_da_capacidade_e_bloqueada(self):
        self.movimentar("entrada", "900")
        with self.assertRaisesMessage(
            CapacidadeArmazemExcedidaError,
            "Capacidade insuficiente",
        ):
            self.movimentar("entrada", "100.001")

    def test_lote_ou_armazem_inativo_nao_recebe_movimento(self):
        self.lote.ativo = False
        self.lote.save(update_fields=("ativo",))
        with self.assertRaisesMessage(ValueError, "precisam estar ativos"):
            self.movimentar("entrada", "10")

    def test_idempotencia_nao_duplica_movimento(self):
        primeiro = self.movimentar(
            "entrada",
            "100",
            chave_idempotencia="planilha-futura:linha-1",
        )
        repetido = self.movimentar(
            "entrada",
            "100",
            chave_idempotencia="planilha-futura:linha-1",
        )
        self.assertEqual(primeiro.id, repetido.id)
        self.assertEqual(MovimentacaoGraos.objects.count(), 1)

    def test_idempotencia_conflitante_e_bloqueada(self):
        self.movimentar(
            "entrada",
            "100",
            chave_idempotencia="referencia-unica",
        )
        with self.assertRaisesMessage(
            MovimentacaoGraosConflitanteError,
            "já foi usada",
        ):
            self.movimentar(
                "entrada",
                "101",
                chave_idempotencia="referencia-unica",
            )

    def test_transferencia_e_atomica(self):
        destino = LoteGraos.objects.create(
            armazem=self.armazem,
            codigo="SOJA-002",
            cultura="Soja",
            safra="2026/2027",
        )
        self.movimentar("entrada", "600")
        transferir_graos(
            usuario=self.usuario,
            lote_origem=self.lote,
            lote_destino=destino,
            quantidade_kg="150",
            data_movimento=timezone.localdate(),
            chave_idempotencia="transferencia-1",
        )
        self.assertEqual(saldo_lote(self.lote), Decimal("450"))
        self.assertEqual(saldo_lote(destino), Decimal("150"))
        self.assertEqual(saldo_armazem(self.armazem), Decimal("600"))

    def test_transferencia_reverte_saida_quando_destino_sem_capacidade(self):
        outro_armazem = ArmazemGraos.objects.create(
            propriedade=self.propriedade,
            nome="Silo pequeno",
            capacidade_kg="100",
        )
        destino = LoteGraos.objects.create(
            armazem=outro_armazem,
            codigo="SOJA-DESTINO",
            cultura="Soja",
            safra="2026/2027",
        )
        self.movimentar("entrada", "600")
        self.movimentar("entrada", "90", lote=destino)
        total_antes = MovimentacaoGraos.objects.count()
        with self.assertRaises(CapacidadeArmazemExcedidaError):
            transferir_graos(
                usuario=self.usuario,
                lote_origem=self.lote,
                lote_destino=destino,
                quantidade_kg="20",
                data_movimento=timezone.localdate(),
            )
        self.assertEqual(MovimentacaoGraos.objects.count(), total_antes)
        self.assertEqual(saldo_lote(self.lote), Decimal("600"))
        self.assertEqual(saldo_lote(destino), Decimal("90"))

    def test_posicao_e_resumo_refletem_ledger(self):
        self.movimentar("entrada", "500")
        self.movimentar("saida", "25")
        posicao = posicao_graos(
            propriedade=self.propriedade.id,
            cultura="soja",
            safra="2026/2027",
        )
        self.assertEqual(posicao[0]["saldo_kg"], Decimal("475"))
        resumo = resumo_graos(propriedade=self.propriedade.id)
        self.assertEqual(resumo["lotes"], 1)
        self.assertEqual(resumo["lotes_com_saldo"], 1)
        self.assertEqual(resumo["saldo_total_kg"], Decimal("475"))

    def test_movimento_protege_lote_de_exclusao(self):
        self.movimentar("entrada", "10")
        with self.assertRaises(ProtectedError):
            self.lote.delete()


class GraosApiTests(GraosBase, APITestCase):
    def setUp(self):
        self.criar_dados()
        self.client.force_authenticate(self.usuario)

    def test_autenticacao_e_obrigatoria(self):
        self.client.force_authenticate(None)
        for url in (
            "/api/graos/armazens/",
            "/api/graos/lotes/",
            "/api/graos/movimentacoes/",
        ):
            self.assertEqual(self.client.get(url).status_code, 401)

    def test_crud_e_filtros_dos_cadastros(self):
        armazens = self.client.get(
            f"/api/graos/armazens/?propriedade={self.propriedade.id}&search=principal"
        )
        self.assertEqual(armazens.status_code, 200)
        self.assertEqual(len(armazens.data), 1)
        lote = self.client.get(
            f"/api/graos/lotes/?cultura=soja&safra=2026/2027"
        )
        self.assertEqual(lote.status_code, 200)
        self.assertEqual(lote.data[0]["propriedade_nome"], self.propriedade.nome)

    def test_fluxo_http_movimento_posicao_e_resumo(self):
        movimento = self.client.post(
            "/api/graos/movimentacoes/",
            {
                "tipo": "entrada",
                "lote": self.lote.id,
                "quantidade_kg": "500.250",
                "data_movimento": str(timezone.localdate()),
                "referencia_externa": "ROM-100",
                "chave_idempotencia": "api:rom-100",
            },
            format="json",
        )
        self.assertEqual(movimento.status_code, 201, movimento.data)
        self.assertEqual(movimento.data["propriedade_id"], self.propriedade.id)

        posicao = self.client.get(
            f"/api/graos/lotes/posicao/?propriedade={self.propriedade.id}"
        )
        self.assertEqual(posicao.status_code, 200)
        self.assertEqual(
            Decimal(posicao.data[0]["saldo_kg"]),
            Decimal("500.250"),
        )
        resumo = self.client.get(
            f"/api/graos/lotes/resumo/?propriedade={self.propriedade.id}"
        )
        self.assertEqual(resumo.status_code, 200)
        self.assertEqual(Decimal(resumo.data["saldo_total_kg"]), Decimal("500.250"))

    def test_movimentos_sao_imutaveis_pela_api(self):
        movimento = self.movimentar("entrada", "100")
        url = f"/api/graos/movimentacoes/{movimento.id}/"
        self.assertEqual(
            self.client.patch(url, {"quantidade_kg": "200"}).status_code,
            405,
        )
        self.assertEqual(self.client.delete(url).status_code, 405)

    def test_contexto_do_lote_movimentado_e_imutavel(self):
        self.movimentar("entrada", "100")
        resposta = self.client.patch(
            f"/api/graos/lotes/{self.lote.id}/",
            {"cultura": "Milho"},
            format="json",
        )
        self.assertEqual(resposta.status_code, 400)
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.cultura, "Soja")

    def test_transferencia_http(self):
        destino = LoteGraos.objects.create(
            armazem=self.armazem,
            codigo="SOJA-API-DESTINO",
            cultura="Soja",
            safra="2026/2027",
        )
        self.movimentar("entrada", "400")
        resposta = self.client.post(
            f"/api/graos/lotes/{self.lote.id}/transferir/",
            {
                "lote_destino": destino.id,
                "quantidade_kg": "125",
                "data_movimento": str(timezone.localdate()),
                "chave_idempotencia": "transferencia-api-1",
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.assertEqual(saldo_lote(self.lote), Decimal("275"))
        self.assertEqual(saldo_lote(destino), Decimal("125"))

    def test_filtro_invalido_retorna_400(self):
        resposta = self.client.get("/api/graos/lotes/posicao/?propriedade=invalida")
        self.assertEqual(resposta.status_code, 400)

    def test_capacidade_nao_pode_ficar_abaixo_da_ocupacao(self):
        self.movimentar("entrada", "500")
        resposta = self.client.patch(
            f"/api/graos/armazens/{self.armazem.id}/",
            {"capacidade_kg": "499"},
            format="json",
        )
        self.assertEqual(resposta.status_code, 400)
        self.assertIn("capacidade_kg", resposta.data)

from decimal import Decimal

from django.urls import reverse
from rest_framework.test import APITestCase

from apps.cadpro.models import CADProPropriedade
from apps.graos.models import LoteGraos, MovimentacaoGraos, PosicaoSaldoGraos
from apps.graos.services import creditar_producao, reservar_saldo
from apps.propriedades.models import Propriedade

from .models import VendaGraos
from .services import criar_rascunho
from .tests import ContextoVendaMixin


class VendaPropriedadeProdutoraTests(ContextoVendaMixin, APITestCase):
    def setUp(self):
        self.criar_contexto()
        self.client.force_authenticate(self.usuario)
        self.url = reverse("vendas-graos-list")
        self.produtoras = []
        self.lotes = []
        self.posicoes = []
        for nome in ("Produtora Norte", "Produtora Sul"):
            propriedade = Propriedade.objects.create(
                nome=nome, municipio="Sorriso", uf="MT", area_hectares="100",
            )
            CADProPropriedade.objects.create(cad_pro=self.cadpro, propriedade=propriedade)
            lote = LoteGraos.objects.create(
                propriedade=propriedade, cad_pro=self.cadpro, armazem=self.armazem,
                codigo=nome, cultura=self.lote.cultura, safra=self.lote.safra,
                classificacao_codigo=self.lote.classificacao_codigo,
            )
            resultado = creditar_producao(
                usuario=self.usuario, lote=lote, quantidade_kg="1000",
                chave_idempotencia=f"credito-{nome}",
            )
            self.produtoras.append(propriedade)
            self.lotes.append(lote)
            self.posicoes.append(PosicaoSaldoGraos.objects.get(pk=resultado.posicoes[0].id))

    def criar_venda(self, indice=1, numero="PROD-1"):
        return criar_rascunho(
            usuario=self.usuario, posicao=self.posicoes[indice], numero_contrato=numero,
            cliente_nome="Cliente de teste", quantidade_kg="600",
            chave_idempotencia=f"criar-{numero}",
        )

    def acao(self, venda, acao, dados=None):
        return self.client.post(
            reverse(f"vendas-graos-{acao}", args=(venda.pk,)), dados or {},
            format="json", HTTP_IDEMPOTENCY_KEY=f"{acao}-{venda.pk}",
        )

    def test_lote_operacional_respeita_propriedade_da_posicao(self):
        venda = self.criar_venda()
        self.assertEqual(venda.lote_id, self.lotes[1].pk)

    def test_ciclo_comercial_movimenta_somente_propriedade_vendida(self):
        venda = self.criar_venda()
        for acao, dados, status_esperado in (
            ("confirmar", {}, 200),
            ("entregar", {"quantidade_kg": "200"}, 201),
            ("devolver", {"quantidade_kg": "50"}, 201),
            ("cancelar", {}, 200),
        ):
            resposta = self.acao(venda, acao, dados)
            self.assertEqual(resposta.status_code, status_esperado, resposta.data)
        for posicao in (self.posicao, *self.posicoes):
            posicao.refresh_from_db()
        self.assertEqual(self.posicao.saldo_fisico_kg, Decimal("1000"))
        self.assertEqual(self.posicoes[0].saldo_fisico_kg, Decimal("1000"))
        self.assertEqual(self.posicoes[1].saldo_fisico_kg, Decimal("850"))
        self.assertEqual(self.posicoes[1].saldo_comprometido_kg, Decimal("0"))
        venda.refresh_from_db()
        self.assertEqual(venda.reserva.posicao_id, venda.posicao_id)
        self.assertEqual(venda.status, VendaGraos.Status.CANCELADA)

    def test_api_filtra_e_identifica_produtora_sem_usar_dona_do_armazem(self):
        venda_a = self.criar_venda(0, "PROD-A")
        venda_b = self.criar_venda(1, "PROD-B")
        for indice, venda in enumerate((venda_a, venda_b)):
            resposta = self.client.get(self.url, {"propriedade": self.produtoras[indice].pk})
            self.assertEqual(resposta.status_code, 200, resposta.data)
            self.assertEqual([item["id"] for item in resposta.data], [venda.pk])
            self.assertEqual(resposta.data[0]["propriedade"], self.produtoras[indice].pk)
            self.assertEqual(resposta.data[0]["propriedade_nome"], self.produtoras[indice].nome)
        self.assertEqual(self.client.get(self.url, {"propriedade": self.propriedade.pk}).data, [])

    def test_armazem_externo_preserva_propriedade_e_historico_nulo_nao_inventa_origem(self):
        self.armazem.propriedade = None
        self.armazem.save(update_fields=("propriedade",))
        venda = self.criar_venda()
        resposta = self.client.get(reverse("vendas-graos-detail", args=(venda.pk,)))
        self.assertEqual(resposta.data["propriedade"], self.produtoras[1].pk)
        self.assertEqual(resposta.data["propriedade_nome"], self.produtoras[1].nome)
        historica = self.rascunho(numero="HISTORICA")
        resposta = self.client.get(reverse("vendas-graos-detail", args=(historica.pk,)))
        self.assertIsNone(resposta.data["propriedade"])
        self.assertIn("propriedade_nome", resposta.data)
        self.assertIsNone(resposta.data["propriedade_nome"])

    def test_rascunho_com_lote_incompativel_nao_reserva_outra_propriedade(self):
        venda = self.criar_venda()
        # Representa um rascunho antigo que recebeu o adaptador errado.
        VendaGraos.objects.filter(pk=venda.pk).update(lote=self.lotes[0])
        antes = MovimentacaoGraos.objects.count()
        resposta = self.acao(venda, "confirmar")
        self.assertEqual(resposta.status_code, 409, resposta.data)
        self.assertEqual(MovimentacaoGraos.objects.count(), antes)
        venda.refresh_from_db()
        self.assertIsNone(venda.reserva_id)
        self.assertEqual(venda.status, VendaGraos.Status.RASCUNHO)

    def test_reserva_incompativel_nao_libera_nem_entrega_saldo_de_outra_posicao(self):
        venda = self.criar_venda()
        reserva = reservar_saldo(
            usuario=self.usuario, lote=self.lotes[0], quantidade_kg="600",
            chave_idempotencia="reserva-incompativel",
        )
        VendaGraos.objects.filter(pk=venda.pk).update(
            status=VendaGraos.Status.CONFIRMADA, reserva_id=reserva.reserva.id,
        )
        antes = MovimentacaoGraos.objects.count()
        for acao in ("entregar", "cancelar"):
            with self.subTest(acao=acao):
                resposta = self.acao(venda, acao, {"quantidade_kg": "100"})
                self.assertEqual(resposta.status_code, 409, resposta.data)
                self.assertEqual(MovimentacaoGraos.objects.count(), antes)

    def test_entrega_de_rascunho_retorna_conflito_sem_erro_interno(self):
        resposta = self.acao(self.criar_venda(), "entregar", {"quantidade_kg": "100"})
        self.assertEqual(resposta.status_code, 409, resposta.data)

    def test_devolucao_com_lote_incompativel_nao_credita_outra_propriedade(self):
        venda = self.criar_venda()
        self.assertEqual(self.acao(venda, "confirmar").status_code, 200)
        self.assertEqual(self.acao(venda, "entregar", {"quantidade_kg": "200"}).status_code, 201)
        VendaGraos.objects.filter(pk=venda.pk).update(lote=self.lotes[0])
        antes = MovimentacaoGraos.objects.count()
        resposta = self.acao(venda, "devolver", {"quantidade_kg": "50"})
        self.assertEqual(resposta.status_code, 409, resposta.data)
        self.assertEqual(MovimentacaoGraos.objects.count(), antes)
        self.posicoes[0].refresh_from_db()
        self.posicoes[1].refresh_from_db()
        self.assertEqual(self.posicoes[0].saldo_fisico_kg, Decimal("1000"))
        self.assertEqual(self.posicoes[1].saldo_fisico_kg, Decimal("800"))

    def test_opcoes_de_posicao_identificam_produtora_e_historico_nulo(self):
        resposta = self.client.get(reverse("saldos-graos-list"))
        self.assertEqual(resposta.status_code, 200, resposta.data)
        nomes = {item["id"]: item["propriedade_nome"] for item in resposta.data}
        self.assertEqual(nomes[self.posicoes[0].pk], self.produtoras[0].nome)
        self.assertEqual(nomes[self.posicoes[1].pk], self.produtoras[1].nome)
        self.assertIsNone(nomes[self.posicao.pk])

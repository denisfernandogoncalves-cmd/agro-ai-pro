from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from threading import Barrier

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db import close_old_connections, connection
from django.test import RequestFactory, TestCase, TransactionTestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.cadpro.models import CADPro, CADProPropriedade
from apps.graos.cargas_services import registrar_carga_colhida
from apps.graos.models import (
    ArmazemGraos,
    GrupoColheita,
    LoteGraos,
    MovimentacaoGraos,
    PosicaoSaldoGraos,
)
from apps.graos.services import creditar_producao
from apps.propriedades.models import Propriedade

from .models import DevolucaoVendaGraos, EntregaVendaGraos, VendaGraos
from .services import (
    VendaGraosConflitoError,
    cancelar_venda,
    confirmar_venda,
    criar_rascunho,
    registrar_devolucao_venda,
    registrar_entrega_venda,
)


class ContextoVendaMixin:
    def criar_contexto(self, *, saldo="1000.000"):
        self.usuario = get_user_model().objects.create_user(
            username="comercial", password="senha-segura"
        )
        self.propriedade = Propriedade.objects.create(
            nome="Fazenda Comercial", municipio="Sorriso", uf="MT",
            area_hectares="900.00",
        )
        self.cadpro = CADPro.objects.create(
            codigo="CAD/PRO VENDAS", descricao="Titular comercial"
        )
        CADProPropriedade.objects.create(
            cad_pro=self.cadpro, propriedade=self.propriedade
        )
        self.armazem = ArmazemGraos.objects.create(
            propriedade=self.propriedade,
            nome="Silo Vendas",
            capacidade_kg="100000.000",
        )
        self.lote = LoteGraos.objects.create(
            armazem=self.armazem,
            cad_pro=self.cadpro,
            codigo="LOTE-VENDA",
            cultura="Soja",
            safra="2026/2027",
            classificacao_codigo="TIPO-1",
        )
        creditar_producao(
            usuario=self.usuario,
            lote=self.lote,
            quantidade_kg=saldo,
            chave_idempotencia=f"producao-base-{self.cadpro.pk}",
        )
        self.posicao = PosicaoSaldoGraos.objects.get(cad_pro=self.cadpro)

    def rascunho(self, *, numero="CTR-001", quantidade="600.000", chave=None):
        return criar_rascunho(
            usuario=self.usuario,
            posicao=self.posicao,
            numero_contrato=numero,
            cliente_nome="Cooperativa Cliente",
            quantidade_kg=quantidade,
            chave_idempotencia=chave or f"criar-{numero}",
            data_contrato=date(2026, 8, 12),
        )


class VendaGraosServiceTests(ContextoVendaMixin, TestCase):
    def setUp(self):
        self.criar_contexto()

    def test_rascunho_nao_altera_saldo_e_confirmacao_reserva(self):
        venda = self.rascunho()
        self.posicao.refresh_from_db()
        self.assertEqual(venda.status, VendaGraos.Status.RASCUNHO)
        self.assertEqual(self.posicao.saldo_comprometido_kg, Decimal("0.000"))

        confirmar_venda(
            usuario=self.usuario, venda=venda, chave_idempotencia="confirmar-1"
        )
        venda.refresh_from_db()
        self.posicao.refresh_from_db()
        self.assertEqual(venda.status, VendaGraos.Status.CONFIRMADA)
        self.assertEqual(self.posicao.saldo_comprometido_kg, Decimal("600.000"))
        self.assertEqual(self.posicao.saldo_disponivel_kg, Decimal("400.000"))

    def test_venda_acima_do_disponivel_e_bloqueada_sem_efeito(self):
        venda = self.rascunho(quantidade="1000.001")
        with self.assertRaisesRegex(Exception, "insuficiente"):
            confirmar_venda(
                usuario=self.usuario,
                venda=venda,
                chave_idempotencia="confirmar-excesso",
            )
        self.posicao.refresh_from_db()
        self.assertEqual(self.posicao.saldo_comprometido_kg, Decimal("0.000"))

    def test_cancelamento_libera_somente_comprometido_aberto(self):
        venda = self.rascunho()
        confirmar_venda(usuario=self.usuario, venda=venda, chave_idempotencia="c1")
        registrar_entrega_venda(
            usuario=self.usuario, venda=venda, quantidade_kg="200",
            chave_idempotencia="e1",
        )
        cancelar_venda(
            usuario=self.usuario, venda=venda, chave_idempotencia="x1"
        )
        venda.refresh_from_db()
        self.posicao.refresh_from_db()
        self.assertEqual(venda.quantidade_entregue_kg, Decimal("200.000"))
        self.assertEqual(venda.quantidade_cancelada_kg, Decimal("400.000"))
        self.assertEqual(self.posicao.saldo_fisico_kg, Decimal("800.000"))
        self.assertEqual(self.posicao.saldo_comprometido_kg, Decimal("0.000"))

    def test_entrega_parcial_total_e_ausencia_de_dupla_baixa(self):
        venda = self.rascunho()
        confirmar_venda(usuario=self.usuario, venda=venda, chave_idempotencia="c2")
        primeira = registrar_entrega_venda(
            usuario=self.usuario, venda=venda, quantidade_kg="200",
            chave_idempotencia="e2",
        )
        repetida = registrar_entrega_venda(
            usuario=self.usuario, venda=venda, quantidade_kg="200",
            chave_idempotencia="e2",
        )
        self.assertEqual(primeira.pk, repetida.pk)
        self.assertEqual(EntregaVendaGraos.objects.count(), 1)
        registrar_entrega_venda(
            usuario=self.usuario, venda=venda, quantidade_kg="400",
            chave_idempotencia="e3",
        )
        venda.refresh_from_db()
        self.posicao.refresh_from_db()
        self.assertEqual(venda.status, VendaGraos.Status.ENTREGUE)
        self.assertEqual(venda.quantidade_entregue_kg, Decimal("600.000"))
        self.assertEqual(self.posicao.saldo_fisico_kg, Decimal("400.000"))
        self.assertEqual(self.posicao.saldo_comprometido_kg, Decimal("0.000"))
        self.assertEqual(
            MovimentacaoGraos.objects.filter(
                operacao=MovimentacaoGraos.Operacao.ENTREGA
            ).count(),
            2,
        )

    def test_entrega_acima_da_reserva_e_bloqueada(self):
        venda = self.rascunho(quantidade="300")
        confirmar_venda(usuario=self.usuario, venda=venda, chave_idempotencia="c3")
        with self.assertRaisesRegex(VendaGraosConflitoError, "excede"):
            registrar_entrega_venda(
                usuario=self.usuario, venda=venda, quantidade_kg="300.001",
                chave_idempotencia="e4",
            )
        self.posicao.refresh_from_db()
        self.assertEqual(self.posicao.saldo_fisico_kg, Decimal("1000.000"))

    def test_devolucao_parcial_total_recompoe_fisico_sem_reabrir_reserva(self):
        venda = self.rascunho(quantidade="300")
        confirmar_venda(usuario=self.usuario, venda=venda, chave_idempotencia="c4")
        registrar_entrega_venda(
            usuario=self.usuario, venda=venda, quantidade_kg="300",
            chave_idempotencia="e5",
        )
        primeira = registrar_devolucao_venda(
            usuario=self.usuario, venda=venda, quantidade_kg="100",
            chave_idempotencia="d1",
        )
        repetida = registrar_devolucao_venda(
            usuario=self.usuario, venda=venda, quantidade_kg="100",
            chave_idempotencia="d1",
        )
        self.assertEqual(primeira.pk, repetida.pk)
        registrar_devolucao_venda(
            usuario=self.usuario, venda=venda, quantidade_kg="200",
            chave_idempotencia="d2",
        )
        venda.refresh_from_db()
        self.posicao.refresh_from_db()
        self.assertEqual(DevolucaoVendaGraos.objects.count(), 2)
        self.assertEqual(venda.status, VendaGraos.Status.ENTREGUE)
        self.assertEqual(venda.quantidade_devolvida_kg, Decimal("300.000"))
        self.assertEqual(venda.reserva.saldo_reservado_kg, Decimal("0.000"))
        self.assertEqual(self.posicao.saldo_fisico_kg, Decimal("1000.000"))
        self.assertEqual(self.posicao.saldo_comprometido_kg, Decimal("0.000"))

    def test_idempotencia_e_conflito_de_payload(self):
        venda = self.rascunho(chave="criar-idem")
        mesma = self.rascunho(chave="criar-idem")
        self.assertEqual(venda.pk, mesma.pk)
        with self.assertRaises(VendaGraosConflitoError):
            criar_rascunho(
                usuario=self.usuario, posicao=self.posicao,
                numero_contrato="CTR-DIF", cliente_nome="Outro",
                quantidade_kg="10", chave_idempotencia="criar-idem",
            )
        confirmar_venda(usuario=self.usuario, venda=venda, chave_idempotencia="conf-idem")
        confirmar_venda(usuario=self.usuario, venda=venda, chave_idempotencia="conf-idem")
        self.assertEqual(
            MovimentacaoGraos.objects.filter(
                operacao=MovimentacaoGraos.Operacao.RESERVA
            ).count(), 1
        )


class VendaGraosApiTests(ContextoVendaMixin, APITestCase):
    def setUp(self):
        self.criar_contexto()
        self.url = reverse("vendas-graos-list")

    def test_cors_autoriza_cabecalho_de_idempotencia(self):
        resposta = self.client.options(
            self.url,
            HTTP_ORIGIN="http://localhost:5173",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS=(
                "authorization,content-type,idempotency-key"
            ),
        )
        permitidos = resposta.headers["Access-Control-Allow-Headers"].lower()
        self.assertIn("idempotency-key", permitidos)

    def payload(self):
        return {
            "numero_contrato": "API-001",
            "cliente_nome": "Cliente API",
            "posicao": self.posicao.pk,
            "quantidade_kg": "250.000",
            "data_contrato": "2026-08-12",
        }

    def test_autenticacao_obrigatoria(self):
        resposta = self.client.get(self.url)
        self.assertEqual(resposta.status_code, 401)

    def test_criar_listar_detalhar_confirmar_entregar_devolver_cancelar(self):
        self.client.force_authenticate(self.usuario)
        resposta = self.client.post(
            self.url, self.payload(), format="json", HTTP_IDEMPOTENCY_KEY="api-criar"
        )
        self.assertEqual(resposta.status_code, 201, resposta.data)
        venda_id = resposta.data["id"]
        self.assertEqual(resposta.data["status"], "rascunho")
        confirmar = self.client.post(
            reverse("vendas-graos-confirmar", args=[venda_id]),
            {}, format="json", HTTP_IDEMPOTENCY_KEY="api-confirmar",
        )
        self.assertEqual(confirmar.status_code, 200, confirmar.data)
        entrega = self.client.post(
            reverse("vendas-graos-entregar", args=[venda_id]),
            {"quantidade_kg": "100.000", "data_movimento": "2026-08-12"},
            format="json", HTTP_IDEMPOTENCY_KEY="api-entrega",
        )
        self.assertEqual(entrega.status_code, 201, entrega.data)
        devolucao = self.client.post(
            reverse("vendas-graos-devolver", args=[venda_id]),
            {"quantidade_kg": "40.000", "data_movimento": "2026-08-12"},
            format="json", HTTP_IDEMPOTENCY_KEY="api-devolucao",
        )
        self.assertEqual(devolucao.status_code, 201, devolucao.data)
        cancelar = self.client.post(
            reverse("vendas-graos-cancelar", args=[venda_id]),
            {}, format="json", HTTP_IDEMPOTENCY_KEY="api-cancelar",
        )
        self.assertEqual(cancelar.status_code, 200, cancelar.data)
        self.assertEqual(cancelar.data["status"], "cancelada")

    def test_filtros_e_rastreabilidade_nao_atribuem_origem_fisica_arbitraria(self):
        grupo_a = GrupoColheita.objects.create(
            propriedade=self.propriedade, cad_pro=self.cadpro,
            armazem_padrao=self.armazem, nome="Equipe Comercial A",
            cultura="Milho", safra="2026/2027", criado_por=self.usuario,
        )
        grupo_b = GrupoColheita.objects.create(
            propriedade=self.propriedade, cad_pro=self.cadpro,
            armazem_padrao=self.armazem, nome="Equipe Comercial B",
            cultura="Milho", safra="2026/2027", criado_por=self.usuario,
        )
        carga_a = registrar_carga_colhida(
            usuario=self.usuario, grupo_colheita=grupo_a, armazem=self.armazem,
            data_colheita=date(2026, 8, 12), placa="ABC1D23",
            peso_bruto_kg="500", umidade_percentual="10",
            impureza_percentual="0", defeitos_percentual="0",
            destinado_semente=False,
        )
        carga_b = registrar_carga_colhida(
            usuario=self.usuario, grupo_colheita=grupo_b, armazem=self.armazem,
            data_colheita=date(2026, 8, 13), placa="DEF4G56",
            peso_bruto_kg="400", umidade_percentual="10",
            impureza_percentual="0", defeitos_percentual="0",
            destinado_semente=False,
        )
        self.assertNotEqual(carga_a.lote_id, carga_b.lote_id)
        posicao = PosicaoSaldoGraos.objects.get(
            cad_pro=self.cadpro, cultura="Milho"
        )
        venda = criar_rascunho(
            usuario=self.usuario, posicao=posicao, numero_contrato="RASTRO-1",
            cliente_nome="Rastreável", quantidade_kg="100",
            chave_idempotencia="rastro-criar",
        )
        self.client.force_authenticate(self.usuario)
        resposta = self.client.get(self.url, {
            "cad_pro": str(self.cadpro.pk), "cultura": "milho",
            "safra": "2026/2027", "classificacao_codigo": "padrao",
            "armazem": self.armazem.pk,
        })
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual([item["id"] for item in resposta.data], [venda.pk])
        detalhe = resposta.data[0]
        self.assertEqual(detalhe["posicao"], posicao.pk)
        self.assertFalse(detalhe["origem_fisica_alocada"])
        self.assertIn(detalhe["lote_operacional"], (carga_a.lote_id, carga_b.lote_id))
        self.assertNotIn("lote", detalhe)
        self.assertNotIn("origens_colheita", detalhe)


class VendaGraosAdminTests(ContextoVendaMixin, TestCase):
    def setUp(self):
        self.criar_contexto()
        self.usuario.is_staff = True
        self.usuario.is_superuser = True
        self.usuario.save(update_fields=("is_staff", "is_superuser"))
        self.venda = self.rascunho(quantidade="300")
        confirmar_venda(
            usuario=self.usuario, venda=self.venda,
            chave_idempotencia="admin-confirmar",
        )
        self.entrega = registrar_entrega_venda(
            usuario=self.usuario, venda=self.venda, quantidade_kg="100",
            chave_idempotencia="admin-entrega",
        )
        self.devolucao = registrar_devolucao_venda(
            usuario=self.usuario, venda=self.venda, quantidade_kg="40",
            chave_idempotencia="admin-devolucao",
        )
        self.client.force_login(self.usuario)

    def test_trilha_comercial_pode_ser_consultada_no_admin(self):
        requisicao = RequestFactory().get("/admin/")
        requisicao.user = self.usuario
        for modelo, objeto in (
            (VendaGraos, self.venda),
            (EntregaVendaGraos, self.entrega),
            (DevolucaoVendaGraos, self.devolucao),
        ):
            with self.subTest(modelo=modelo.__name__):
                model_admin = admin.site._registry[modelo]
                self.assertTrue(model_admin.has_view_permission(requisicao, objeto))
                self.assertTrue(
                    model_admin.get_queryset(requisicao).filter(pk=objeto.pk).exists()
                )

    def test_trilha_comercial_nao_pode_ser_editada_ou_excluida_no_admin(self):
        for modelo, objeto in (
            ("vendagraos", self.venda),
            ("entregavendagraos", self.entrega),
            ("devolucaovendagraos", self.devolucao),
        ):
            with self.subTest(modelo=modelo):
                alterar = self.client.post(
                    reverse(f"admin:vendas_{modelo}_change", args=[objeto.pk]),
                    {},
                )
                criar = self.client.get(reverse(f"admin:vendas_{modelo}_add"))
                excluir = self.client.post(
                    reverse(f"admin:vendas_{modelo}_delete", args=[objeto.pk]),
                    {"post": "yes"},
                )
                self.assertEqual(alterar.status_code, 403)
                self.assertEqual(criar.status_code, 403)
                self.assertEqual(excluir.status_code, 403)
                self.assertTrue(type(objeto).objects.filter(pk=objeto.pk).exists())


class VendaGraosConcorrenciaTests(ContextoVendaMixin, TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        if connection.vendor != "postgresql":
            self.skipTest("Concorrência exige PostgreSQL real.")
        self.criar_contexto(saldo="100.000")
        self.venda_a = self.rascunho(numero="CONC-A", quantidade="80")
        self.venda_b = self.rascunho(numero="CONC-B", quantidade="80")

    def test_duas_confirmacoes_disputam_o_mesmo_saldo(self):
        barreira = Barrier(2)

        def confirmar(venda_id, chave):
            close_old_connections()
            try:
                usuario = get_user_model().objects.get(pk=self.usuario.pk)
                venda = VendaGraos.objects.get(pk=venda_id)
                barreira.wait(timeout=10)
                confirmar_venda(
                    usuario=usuario, venda=venda, chave_idempotencia=chave
                )
                return "ok"
            except Exception as exc:  # resultado concorrente esperado
                return getattr(exc, "codigo", exc.__class__.__name__)
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            resultados = list(executor.map(
                lambda args: confirmar(*args),
                ((self.venda_a.pk, "conc-a"), (self.venda_b.pk, "conc-b")),
            ))
        self.assertEqual(resultados.count("ok"), 1, resultados)
        posicao = PosicaoSaldoGraos.objects.get(pk=self.posicao.pk)
        self.assertEqual(posicao.saldo_comprometido_kg, Decimal("80.000"))
        self.assertEqual(posicao.saldo_disponivel_kg, Decimal("20.000"))

    def _executar_movimentos_simultaneos(self, funcao, argumentos):
        barreira = Barrier(2)

        def executar(kwargs):
            close_old_connections()
            try:
                usuario = get_user_model().objects.get(pk=self.usuario.pk)
                venda = VendaGraos.objects.get(pk=self.venda_a.pk)
                barreira.wait(timeout=10)
                movimento = funcao(usuario=usuario, venda=venda, **kwargs)
                return "ok", movimento.pk
            except VendaGraosConflitoError as exc:
                return exc.codigo, None
            except Exception as exc:
                return exc.__class__.__name__, None
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            return list(executor.map(executar, argumentos))

    def test_entrega_concorrente_mesma_chave_mesmo_payload_tem_um_efeito(self):
        confirmar_venda(
            usuario=self.usuario, venda=self.venda_a,
            chave_idempotencia="confirmar-entrega-idem",
        )
        resultados = self._executar_movimentos_simultaneos(
            registrar_entrega_venda,
            (
                {"quantidade_kg": "30", "chave_idempotencia": "entrega-idem"},
                {"quantidade_kg": "30", "chave_idempotencia": "entrega-idem"},
            ),
        )
        self.assertEqual([status for status, _ in resultados], ["ok", "ok"])
        self.assertEqual(len({pk for _, pk in resultados}), 1)
        self.assertEqual(EntregaVendaGraos.objects.count(), 1)
        self.assertEqual(
            MovimentacaoGraos.objects.filter(
                operacao=MovimentacaoGraos.Operacao.ENTREGA
            ).count(),
            1,
        )
        self.venda_a.refresh_from_db()
        self.posicao.refresh_from_db()
        self.assertEqual(self.venda_a.quantidade_entregue_kg, Decimal("30.000"))
        self.assertEqual(self.posicao.saldo_fisico_kg, Decimal("70.000"))

    def test_devolucao_concorrente_mesma_chave_mesmo_payload_tem_um_efeito(self):
        confirmar_venda(
            usuario=self.usuario, venda=self.venda_a,
            chave_idempotencia="confirmar-devolucao-idem",
        )
        registrar_entrega_venda(
            usuario=self.usuario, venda=self.venda_a, quantidade_kg="40",
            chave_idempotencia="entrega-base-devolucao",
        )
        resultados = self._executar_movimentos_simultaneos(
            registrar_devolucao_venda,
            (
                {"quantidade_kg": "20", "chave_idempotencia": "devolucao-idem"},
                {"quantidade_kg": "20", "chave_idempotencia": "devolucao-idem"},
            ),
        )
        self.assertEqual([status for status, _ in resultados], ["ok", "ok"])
        self.assertEqual(len({pk for _, pk in resultados}), 1)
        self.assertEqual(DevolucaoVendaGraos.objects.count(), 1)
        self.assertEqual(
            MovimentacaoGraos.objects.filter(
                operacao=MovimentacaoGraos.Operacao.DEVOLUCAO
            ).count(),
            1,
        )
        self.venda_a.refresh_from_db()
        self.posicao.refresh_from_db()
        self.assertEqual(self.venda_a.quantidade_devolvida_kg, Decimal("20.000"))
        self.assertEqual(self.posicao.saldo_fisico_kg, Decimal("80.000"))

    def test_entrega_concorrente_mesma_chave_payload_diverso_controla_conflito(self):
        confirmar_venda(
            usuario=self.usuario, venda=self.venda_a,
            chave_idempotencia="confirmar-entrega-conflito",
        )
        resultados = self._executar_movimentos_simultaneos(
            registrar_entrega_venda,
            (
                {"quantidade_kg": "10", "chave_idempotencia": "entrega-conflito"},
                {"quantidade_kg": "20", "chave_idempotencia": "entrega-conflito"},
            ),
        )
        self.assertEqual([status for status, _ in resultados].count("ok"), 1)
        self.assertEqual(
            [status for status, _ in resultados].count("conflito"),
            1,
            resultados,
        )
        self.assertEqual(EntregaVendaGraos.objects.count(), 1)
        self.assertEqual(
            MovimentacaoGraos.objects.filter(
                operacao=MovimentacaoGraos.Operacao.ENTREGA
            ).count(),
            1,
        )
        self.venda_a.refresh_from_db()
        self.assertIn(
            self.venda_a.quantidade_entregue_kg,
            (Decimal("10.000"), Decimal("20.000")),
        )

    def test_devolucao_concorrente_mesma_chave_payload_diverso_controla_conflito(self):
        confirmar_venda(
            usuario=self.usuario, venda=self.venda_a,
            chave_idempotencia="confirmar-devolucao-conflito",
        )
        registrar_entrega_venda(
            usuario=self.usuario, venda=self.venda_a, quantidade_kg="40",
            chave_idempotencia="entrega-base-conflito",
        )
        resultados = self._executar_movimentos_simultaneos(
            registrar_devolucao_venda,
            (
                {"quantidade_kg": "10", "chave_idempotencia": "devolucao-conflito"},
                {"quantidade_kg": "20", "chave_idempotencia": "devolucao-conflito"},
            ),
        )
        self.assertEqual([status for status, _ in resultados].count("ok"), 1)
        self.assertEqual(
            [status for status, _ in resultados].count("conflito"),
            1,
            resultados,
        )
        self.assertEqual(DevolucaoVendaGraos.objects.count(), 1)
        self.assertEqual(
            MovimentacaoGraos.objects.filter(
                operacao=MovimentacaoGraos.Operacao.DEVOLUCAO
            ).count(),
            1,
        )
        self.venda_a.refresh_from_db()
        self.assertIn(
            self.venda_a.quantidade_devolvida_kg,
            (Decimal("10.000"), Decimal("20.000")),
        )

from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
from decimal import Decimal
from types import MappingProxyType
from threading import Barrier
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, close_old_connections, connection
from django.db.migrations.executor import MigrationExecutor
from django.db.models import Model
from django.test import TestCase, TransactionTestCase
from django.urls import resolve, reverse
from rest_framework.test import APITestCase

from apps.cadpro.models import CADPro, CADProPropriedade
from apps.propriedades.models import Propriedade

from .events import saldo_graos_alterado
from .models import (
    ArmazemGraos,
    LoteGraos,
    MovimentacaoGraos,
    OrigemSaldoGraos,
    PosicaoSaldoGraos,
    ReservaSaldoGraos,
)
from .services import (
    CapacidadeArmazemExcedidaError,
    MovimentacaoGraosConflitanteError,
    SaldoGraosInsuficienteError,
    SaldoGraosError,
    confirmar_entrega,
    consultar_posicao,
    creditar_producao,
    estornar_movimentacao,
    liberar_reserva,
    reconciliar_posicao,
    registrar_ajuste,
    registrar_devolucao,
    registrar_movimentacao,
    reservar_saldo,
    saldo_lote,
    transferir_graos,
    transferir_saldo_fisico,
)


class GraosSaldoBase:
    def criar_contexto(self):
        self.usuario = get_user_model().objects.create_user("operador_saldos")
        self.propriedade = Propriedade.objects.create(
            nome="Fazenda Saldo",
            municipio="Sorriso",
            uf="MT",
            area_hectares="1000",
        )
        self.cad_pro = CADPro.objects.create(
            codigo="CAD/001",
            descricao="Produtor titular",
        )
        CADProPropriedade.objects.create(
            cad_pro=self.cad_pro,
            propriedade=self.propriedade,
        )
        self.armazem = ArmazemGraos.objects.create(
            propriedade=self.propriedade,
            nome="Silo 1",
            capacidade_kg="2000.000",
        )
        self.lote = LoteGraos.objects.create(
            armazem=self.armazem,
            cad_pro=self.cad_pro,
            codigo="SOJA-001",
            cultura="Soja",
            safra="2026/2027",
            classificacao_codigo="PADRAO",
        )

    def creditar(self, quantidade="1000.000", chave="producao:1"):
        return creditar_producao(
            usuario=self.usuario,
            lote=self.lote,
            quantidade_kg=quantidade,
            chave_idempotencia=chave,
        )


class PosicaoSaldoGraosModelTests(GraosSaldoBase, TestCase):
    def setUp(self):
        self.criar_contexto()

    def test_chave_da_posicao_e_unica_e_disponivel_e_calculado(self):
        resultado = self.creditar()
        posicao = resultado.posicoes[0]
        self.assertEqual(posicao.saldo_disponivel_kg, Decimal("1000.000"))
        with self.assertRaises(IntegrityError):
            PosicaoSaldoGraos.objects.create(
                cad_pro=self.cad_pro,
                cultura="Soja",
                safra="2026/2027",
                classificacao_codigo="PADRAO",
                armazem=self.armazem,
            )

    def test_lote_rejeita_cadpro_sem_vinculo_com_propriedade(self):
        outro = CADPro.objects.create(codigo="CAD-2", descricao="Outro")
        self.lote.cad_pro = outro
        with self.assertRaisesMessage(Exception, "vÃ­nculo ativo"):
            self.lote.full_clean()


class ServicosSaldoGraosTests(GraosSaldoBase, TestCase):
    def setUp(self):
        self.criar_contexto()

    def test_fluxo_credito_reserva_entrega_e_liberacao(self):
        credito = self.creditar()
        reserva_resultado = reservar_saldo(
            usuario=self.usuario,
            lote=self.lote,
            quantidade_kg="300",
            chave_idempotencia="reserva:1",
        )
        entrega = confirmar_entrega(
            usuario=self.usuario,
            reserva=reserva_resultado.reserva,
            quantidade_kg="100",
            chave_idempotencia="entrega:1",
        )
        liberacao = liberar_reserva(
            usuario=self.usuario,
            reserva=reserva_resultado.reserva,
            chave_idempotencia="liberacao:1",
        )
        posicao = consultar_posicao().get(pk=credito.posicoes[0].pk)
        reserva = ReservaSaldoGraos.objects.get(pk=reserva_resultado.reserva.pk)
        self.assertEqual(posicao.saldo_fisico_kg, Decimal("900.000"))
        self.assertEqual(posicao.saldo_comprometido_kg, Decimal("0.000"))
        self.assertEqual(posicao.saldo_disponivel_kg, Decimal("900.000"))
        self.assertEqual(posicao.versao, 4)
        self.assertEqual(reserva.status, ReservaSaldoGraos.Status.LIBERADA)
        self.assertEqual(entrega.movimentacoes[0].delta_fisico_kg, Decimal("-100"))
        self.assertEqual(liberacao.movimentacoes[0].delta_comprometido_kg, Decimal("-200"))

    def test_idempotencia_retorna_mesmo_resultado_e_rejeita_conflito(self):
        primeiro = self.creditar("100", "idem:1")
        repetido = self.creditar("100", "idem:1")
        self.assertTrue(repetido.idempotente)
        self.assertEqual(primeiro.movimentacoes[0].pk, repetido.movimentacoes[0].pk)
        self.assertEqual(MovimentacaoGraos.objects.count(), 1)
        with self.assertRaises(MovimentacaoGraosConflitanteError):
            self.creditar("101", "idem:1")

    def test_replay_retorna_snapshot_original_apos_operacoes_intervenientes(self):
        def confirmar_replay(primeiro, repetido):
            self.assertTrue(repetido.idempotente)
            self.assertEqual(primeiro, replace(repetido, idempotente=False))

        credito = self.creditar("100", "replay:credito")
        self.creditar("50", "replay:credito:interveniente")
        replay_credito = self.creditar("100", "replay:credito")
        confirmar_replay(credito, replay_credito)
        self.assertEqual(
            replay_credito.posicoes[0].saldo_fisico_kg,
            Decimal("100.000"),
        )

        reserva = reservar_saldo(
            usuario=self.usuario,
            lote=self.lote,
            quantidade_kg="30",
            chave_idempotencia="replay:reserva",
        )
        liberacao = liberar_reserva(
            usuario=self.usuario,
            reserva=reserva.reserva,
            quantidade_kg="5",
            chave_idempotencia="replay:liberacao",
        )
        entrega = confirmar_entrega(
            usuario=self.usuario,
            reserva=reserva.reserva,
            quantidade_kg="5",
            chave_idempotencia="replay:entrega",
        )
        liberar_reserva(
            usuario=self.usuario,
            reserva=reserva.reserva,
            quantidade_kg="5",
            chave_idempotencia="replay:liberacao:interveniente",
        )
        confirmar_replay(
            reserva,
            reservar_saldo(
                usuario=self.usuario,
                lote=self.lote,
                quantidade_kg="30",
                chave_idempotencia="replay:reserva",
            ),
        )
        confirmar_replay(
            liberacao,
            liberar_reserva(
                usuario=self.usuario,
                reserva=reserva.reserva,
                quantidade_kg="5",
                chave_idempotencia="replay:liberacao",
            ),
        )
        confirmar_replay(
            entrega,
            confirmar_entrega(
                usuario=self.usuario,
                reserva=reserva.reserva,
                quantidade_kg="5",
                chave_idempotencia="replay:entrega",
            ),
        )

        devolucao = registrar_devolucao(
            usuario=self.usuario,
            lote=self.lote,
            quantidade_kg="10",
            chave_idempotencia="replay:devolucao",
        )
        self.creditar("1", "replay:devolucao:interveniente")
        confirmar_replay(
            devolucao,
            registrar_devolucao(
                usuario=self.usuario,
                lote=self.lote,
                quantidade_kg="10",
                chave_idempotencia="replay:devolucao",
            ),
        )
        ajuste = registrar_ajuste(
            usuario=self.usuario,
            lote=self.lote,
            delta_fisico_kg="-1",
            chave_idempotencia="replay:ajuste",
        )
        self.creditar("1", "replay:ajuste:interveniente")
        confirmar_replay(
            ajuste,
            registrar_ajuste(
                usuario=self.usuario,
                lote=self.lote,
                delta_fisico_kg="-1",
                chave_idempotencia="replay:ajuste",
            ),
        )

        armazem_destino = ArmazemGraos.objects.create(
            propriedade=self.propriedade,
            nome="Silo replay",
            capacidade_kg="2000",
        )
        lote_destino = LoteGraos.objects.create(
            armazem=armazem_destino,
            cad_pro=self.cad_pro,
            codigo="SOJA-REPLAY",
            cultura="Soja",
            safra="2026/2027",
            classificacao_codigo="PADRAO",
        )
        transferencia = transferir_saldo_fisico(
            usuario=self.usuario,
            lote_origem=self.lote,
            lote_destino=lote_destino,
            quantidade_kg="5",
            chave_idempotencia="replay:transferencia",
        )
        registrar_ajuste(
            usuario=self.usuario,
            lote=self.lote,
            delta_fisico_kg="-1",
            chave_idempotencia="replay:transferencia:interveniente",
        )
        confirmar_replay(
            transferencia,
            transferir_saldo_fisico(
                usuario=self.usuario,
                lote_origem=self.lote,
                lote_destino=lote_destino,
                quantidade_kg="5",
                chave_idempotencia="replay:transferencia",
            ),
        )
        estorno = estornar_movimentacao(
            usuario=self.usuario,
            movimentacao=transferencia.movimentacoes[0],
            chave_idempotencia="replay:estorno",
        )
        registrar_ajuste(
            usuario=self.usuario,
            lote=self.lote,
            delta_fisico_kg="-1",
            chave_idempotencia="replay:estorno:interveniente",
        )
        confirmar_replay(
            estorno,
            estornar_movimentacao(
                usuario=self.usuario,
                movimentacao=transferencia.movimentacoes[0],
                chave_idempotencia="replay:estorno",
            ),
        )

        posicao = PosicaoSaldoGraos.objects.get(pk=credito.posicoes[0].id)
        PosicaoSaldoGraos.objects.filter(pk=posicao.pk).update(
            saldo_fisico_kg=posicao.saldo_fisico_kg - Decimal("1")
        )
        reconciliacao = reconciliar_posicao(
            usuario=self.usuario,
            posicao=posicao,
            chave_idempotencia="replay:reconciliacao",
        )
        registrar_ajuste(
            usuario=self.usuario,
            lote=self.lote,
            delta_fisico_kg="-1",
            chave_idempotencia="replay:reconciliacao:interveniente",
        )
        confirmar_replay(
            reconciliacao,
            reconciliar_posicao(
                usuario=self.usuario,
                posicao=posicao,
                chave_idempotencia="replay:reconciliacao",
            ),
        )

        legado = registrar_movimentacao(
            usuario=self.usuario,
            tipo=MovimentacaoGraos.Tipo.SAIDA,
            lote=self.lote,
            quantidade_kg="1",
            chave_idempotencia="replay:adaptador-movimento",
        )
        self.creditar("1", "replay:adaptador-movimento:interveniente")
        replay_legado = registrar_movimentacao(
            usuario=self.usuario,
            tipo=MovimentacaoGraos.Tipo.SAIDA,
            lote=self.lote,
            quantidade_kg="1",
            chave_idempotencia="replay:adaptador-movimento",
        )
        self.assertEqual(legado.pk, replay_legado.pk)
        transferencia_legada = transferir_graos(
            usuario=self.usuario,
            lote_origem=self.lote,
            lote_destino=lote_destino,
            quantidade_kg="1",
            chave_idempotencia="replay:adaptador-transferencia",
        )
        registrar_ajuste(
            usuario=self.usuario,
            lote=self.lote,
            delta_fisico_kg="-1",
            chave_idempotencia="replay:adaptador-transferencia:interveniente",
        )
        replay_transferencia_legada = transferir_graos(
            usuario=self.usuario,
            lote_origem=self.lote,
            lote_destino=lote_destino,
            quantidade_kg="1",
            chave_idempotencia="replay:adaptador-transferencia",
        )
        self.assertEqual(
            tuple(item.pk for item in transferencia_legada),
            tuple(item.pk for item in replay_transferencia_legada),
        )

    def test_todos_os_servicos_mutadores_repetem_sem_novo_efeito(self):
        def executar_duas_vezes(servico, **kwargs):
            primeiro = servico(**kwargs)
            contagens = (
                OrigemSaldoGraos.objects.count(),
                MovimentacaoGraos.objects.count(),
                ReservaSaldoGraos.objects.count(),
            )
            repetido = servico(**kwargs)
            self.assertTrue(repetido.idempotente)
            self.assertEqual(
                tuple(item.pk for item in primeiro.movimentacoes),
                tuple(item.pk for item in repetido.movimentacoes),
            )
            self.assertEqual(
                contagens,
                (
                    OrigemSaldoGraos.objects.count(),
                    MovimentacaoGraos.objects.count(),
                    ReservaSaldoGraos.objects.count(),
                ),
            )
            return primeiro

        credito = executar_duas_vezes(
            creditar_producao,
            usuario=self.usuario,
            lote=self.lote,
            quantidade_kg="800",
            chave_idempotencia="todos:credito",
        )
        reserva = executar_duas_vezes(
            reservar_saldo,
            usuario=self.usuario,
            lote=self.lote,
            quantidade_kg="200",
            chave_idempotencia="todos:reserva",
        ).reserva
        executar_duas_vezes(
            liberar_reserva,
            usuario=self.usuario,
            reserva=reserva,
            quantidade_kg="50",
            chave_idempotencia="todos:liberacao",
        )
        executar_duas_vezes(
            confirmar_entrega,
            usuario=self.usuario,
            reserva=reserva,
            quantidade_kg="50",
            chave_idempotencia="todos:entrega",
        )
        executar_duas_vezes(
            registrar_devolucao,
            usuario=self.usuario,
            lote=self.lote,
            quantidade_kg="10",
            chave_idempotencia="todos:devolucao",
        )
        ajuste = executar_duas_vezes(
            registrar_ajuste,
            usuario=self.usuario,
            lote=self.lote,
            delta_fisico_kg="-10",
            chave_idempotencia="todos:ajuste",
        )
        armazem_destino = ArmazemGraos.objects.create(
            propriedade=self.propriedade,
            nome="Silo idempotÃªncia",
            capacidade_kg="2000",
        )
        lote_destino = LoteGraos.objects.create(
            armazem=armazem_destino,
            cad_pro=self.cad_pro,
            codigo="SOJA-IDEM",
            cultura="Soja",
            safra="2026/2027",
            classificacao_codigo="PADRAO",
        )
        transferencia = executar_duas_vezes(
            transferir_saldo_fisico,
            usuario=self.usuario,
            lote_origem=self.lote,
            lote_destino=lote_destino,
            quantidade_kg="100",
            chave_idempotencia="todos:transferencia",
        )
        executar_duas_vezes(
            estornar_movimentacao,
            usuario=self.usuario,
            movimentacao=transferencia.movimentacoes[0],
            chave_idempotencia="todos:estorno",
        )
        executar_duas_vezes(
            reconciliar_posicao,
            usuario=self.usuario,
            posicao=credito.posicoes[0],
            chave_idempotencia="todos:reconciliacao",
        )

        movimento_legado = registrar_movimentacao(
            usuario=self.usuario,
            tipo=MovimentacaoGraos.Tipo.SAIDA,
            lote=self.lote,
            quantidade_kg="1",
            chave_idempotencia="todos:adaptador-movimento",
        )
        repetido_legado = registrar_movimentacao(
            usuario=self.usuario,
            tipo=MovimentacaoGraos.Tipo.SAIDA,
            lote=self.lote,
            quantidade_kg="1",
            chave_idempotencia="todos:adaptador-movimento",
        )
        self.assertEqual(movimento_legado.pk, repetido_legado.pk)
        transferencia_legada = transferir_graos(
            usuario=self.usuario,
            lote_origem=self.lote,
            lote_destino=lote_destino,
            quantidade_kg="1",
            chave_idempotencia="todos:adaptador-transferencia",
        )
        repetida_legada = transferir_graos(
            usuario=self.usuario,
            lote_origem=self.lote,
            lote_destino=lote_destino,
            quantidade_kg="1",
            chave_idempotencia="todos:adaptador-transferencia",
        )
        self.assertEqual(
            tuple(item.pk for item in transferencia_legada),
            tuple(item.pk for item in repetida_legada),
        )
        self.assertIsNotNone(ajuste.movimentacoes[0].pk)

    def test_contrato_e_snapshots_sao_imutaveis(self):
        resultado = creditar_producao(
            usuario=self.usuario,
            lote=self.lote,
            quantidade_kg="100",
            chave_idempotencia="imutavel:contrato",
            metadados={"externo": {"itens": ["A", {"valor": "B"}]}},
        )
        movimento = resultado.movimentacoes[0]
        self.assertIsInstance(resultado.detalhes, MappingProxyType)
        self.assertEqual(movimento.snapshot_anterior["saldo_fisico_kg"], "0.000")
        self.assertEqual(movimento.snapshot_posterior["saldo_fisico_kg"], "100.000")

        reserva = reservar_saldo(
            usuario=self.usuario,
            lote=self.lote,
            quantidade_kg="10",
            chave_idempotencia="imutavel:reserva",
        ).reserva
        posicao_modelo = PosicaoSaldoGraos.objects.get(pk=resultado.posicoes[0].id)
        PosicaoSaldoGraos.objects.filter(pk=posicao_modelo.pk).update(
            saldo_fisico_kg="99"
        )
        reconciliacao = reconciliar_posicao(
            usuario=self.usuario,
            posicao=posicao_modelo,
            chave_idempotencia="imutavel:detalhes",
        )
        objetos = (
            resultado,
            resultado.origem,
            resultado.posicoes[0],
            movimento,
            reserva,
        )
        for objeto in objetos:
            self.assertTrue(is_dataclass(objeto))
            self.assertNotIsInstance(objeto, Model)
            with self.assertRaises(FrozenInstanceError):
                setattr(objeto, fields(objeto)[0].name, "alterado")
        for mapping in (
            resultado.origem.metadados,
            resultado.origem.metadados["externo"],
            movimento.snapshot_anterior,
            movimento.snapshot_posterior,
            reconciliacao.detalhes,
            reconciliacao.detalhes["antes"],
            reconciliacao.detalhes["depois"],
        ):
            self.assertIsInstance(mapping, MappingProxyType)
            with self.assertRaises(TypeError):
                mapping["alterado"] = True
        self.assertIsInstance(
            resultado.origem.metadados["externo"]["itens"], tuple
        )
        with self.assertRaises(TypeError):
            resultado.origem.metadados["externo"]["itens"][1]["valor"] = "C"

    def test_movimentacao_e_imutavel_no_modelo_e_querysets_do_orm(self):
        movimento_id = self.creditar("100", "imutavel:orm").movimentacoes[0].id
        movimento = MovimentacaoGraos.objects.get(pk=movimento_id)
        movimento.observacoes = "tentativa"
        with self.assertRaises(ValidationError):
            movimento.save()
        with self.assertRaises(ValidationError):
            MovimentacaoGraos.objects.filter(pk=movimento.pk).update(
                observacoes="tentativa"
            )
        with self.assertRaises(ValidationError):
            MovimentacaoGraos.objects.filter(pk=movimento.pk).delete()
        with self.assertRaises(ValidationError):
            movimento.delete()

    def test_reserva_nao_pode_superar_disponivel(self):
        self.creditar("100")
        with self.assertRaises(SaldoGraosInsuficienteError):
            reservar_saldo(
                usuario=self.usuario,
                lote=self.lote,
                quantidade_kg="100.001",
                chave_idempotencia="reserva:sem-saldo",
            )
        self.assertFalse(
            OrigemSaldoGraos.objects.filter(
                chave_idempotencia="reserva:sem-saldo"
            ).exists()
        )

    def test_capacidade_e_validada_transacionalmente(self):
        self.creditar("1900")
        with self.assertRaises(CapacidadeArmazemExcedidaError):
            registrar_devolucao(
                usuario=self.usuario,
                lote=self.lote,
                quantidade_kg="101",
                chave_idempotencia="devolucao:excede",
            )
        self.assertEqual(saldo_lote(self.lote), Decimal("1900.000"))

    def test_ajuste_devolucao_e_estorno_preservam_ledger(self):
        credito = self.creditar("500")
        ajuste = registrar_ajuste(
            usuario=self.usuario,
            lote=self.lote,
            delta_fisico_kg="-20",
            chave_idempotencia="ajuste:1",
        )
        registrar_devolucao(
            usuario=self.usuario,
            lote=self.lote,
            quantidade_kg="5",
            chave_idempotencia="devolucao:1",
        )
        estorno = estornar_movimentacao(
            usuario=self.usuario,
            movimentacao=ajuste.movimentacoes[0],
            chave_idempotencia="estorno:1",
        )
        posicao = consultar_posicao().get(pk=credito.posicoes[0].pk)
        self.assertEqual(posicao.saldo_fisico_kg, Decimal("505.000"))
        self.assertEqual(
            estorno.movimentacoes[0].estorno_de_id,
            ajuste.movimentacoes[0].id,
        )

    def test_transferencia_bloqueia_disponivel_e_atualiza_duas_posicoes(self):
        outro_armazem = ArmazemGraos.objects.create(
            propriedade=self.propriedade,
            nome="Silo 2",
            capacidade_kg="1000",
        )
        destino = LoteGraos.objects.create(
            armazem=outro_armazem,
            cad_pro=self.cad_pro,
            codigo="SOJA-DEST",
            cultura="Soja",
            safra="2026/2027",
            classificacao_codigo="PADRAO",
        )
        self.creditar("600")
        reserva = reservar_saldo(
            usuario=self.usuario,
            lote=self.lote,
            quantidade_kg="200",
            chave_idempotencia="reserva:transferencia",
        )
        with self.assertRaises(SaldoGraosInsuficienteError):
            transferir_saldo_fisico(
                usuario=self.usuario,
                lote_origem=self.lote,
                lote_destino=destino,
                quantidade_kg="401",
                chave_idempotencia="transferencia:falha",
            )
        resultado = transferir_saldo_fisico(
            usuario=self.usuario,
            lote_origem=self.lote,
            lote_destino=destino,
            quantidade_kg="150",
            chave_idempotencia="transferencia:ok",
        )
        saldos = sorted(item.saldo_fisico_kg for item in resultado.posicoes)
        self.assertEqual(saldos, [Decimal("150.000"), Decimal("450.000")])
        self.assertEqual(len(resultado.movimentacoes), 2)
        ReservaSaldoGraos.objects.get(pk=reserva.reserva.id)

    def test_estorno_de_transferencia_sempre_inverte_as_duas_pernas(self):
        destino_armazem = ArmazemGraos.objects.create(
            propriedade=self.propriedade,
            nome="Silo destino",
            capacidade_kg="2000",
        )
        destino = LoteGraos.objects.create(
            armazem=destino_armazem,
            cad_pro=self.cad_pro,
            codigo="SOJA-ESTORNO",
            cultura="Soja",
            safra="2026/2027",
            classificacao_codigo="PADRAO",
        )
        self.creditar("500", "transferencia:credito")
        transferencia = transferir_saldo_fisico(
            usuario=self.usuario,
            lote_origem=self.lote,
            lote_destino=destino,
            quantidade_kg="200",
            chave_idempotencia="transferencia:estornar",
        )
        resultado = estornar_movimentacao(
            usuario=self.usuario,
            movimentacao=transferencia.movimentacoes[0],
            chave_idempotencia="estorno:transferencia",
        )
        self.assertEqual(resultado.codigo, "transferencia_estornada")
        self.assertEqual(len(resultado.movimentacoes), 2)
        self.assertEqual(
            {item.estorno_de_id for item in resultado.movimentacoes},
            {item.pk for item in transferencia.movimentacoes},
        )
        saldos = {
            item.armazem_id: item.saldo_fisico_kg for item in resultado.posicoes
        }
        self.assertEqual(saldos[str(self.armazem.pk)], Decimal("500.000"))
        self.assertEqual(saldos[str(destino_armazem.pk)], Decimal("0.000"))
        with self.assertRaisesMessage(SaldoGraosError, "jÃ¡ foi estornada"):
            estornar_movimentacao(
                usuario=self.usuario,
                movimentacao=transferencia.movimentacoes[1],
                chave_idempotencia="estorno:individual-proibido",
            )

    def test_cadpro_inativo_bloqueia_todos_os_mutadores_de_posicao_existente(self):
        credito = self.creditar("500", "inativo:credito")
        reserva = reservar_saldo(
            usuario=self.usuario,
            lote=self.lote,
            quantidade_kg="100",
            chave_idempotencia="inativo:reserva",
        ).reserva
        self.cad_pro.ativo = False
        self.cad_pro.save(update_fields=("ativo",))
        chamadas = (
            lambda: registrar_ajuste(
                usuario=self.usuario, lote=self.lote, delta_fisico_kg="-1",
                chave_idempotencia="inativo:ajuste",
            ),
            lambda: liberar_reserva(
                usuario=self.usuario, reserva=reserva, quantidade_kg="1",
                chave_idempotencia="inativo:liberar",
            ),
            lambda: confirmar_entrega(
                usuario=self.usuario, reserva=reserva, quantidade_kg="1",
                chave_idempotencia="inativo:entrega",
            ),
            lambda: estornar_movimentacao(
                usuario=self.usuario, movimentacao=credito.movimentacoes[0],
                chave_idempotencia="inativo:estorno",
            ),
            lambda: reconciliar_posicao(
                usuario=self.usuario, posicao=credito.posicoes[0],
                chave_idempotencia="inativo:reconciliar",
            ),
        )
        for chamada in chamadas:
            with self.assertRaisesMessage(SaldoGraosError, "CAD/PRO"):
                chamada()

    def test_reconciliacao_corrige_snapshot_pelo_ledger(self):
        resultado = self.creditar("250")
        posicao = resultado.posicoes[0]
        PosicaoSaldoGraos.objects.filter(pk=posicao.pk).update(saldo_fisico_kg="1")
        reconciliado = reconciliar_posicao(
            usuario=self.usuario,
            posicao=posicao,
            chave_idempotencia="reconciliacao:1",
        )
        self.assertTrue(reconciliado.detalhes["divergente"])
        self.assertEqual(reconciliado.posicoes[0].saldo_fisico_kg, Decimal("250.000"))

    def test_evento_so_e_publicado_apos_commit(self):
        recebidos = []

        def receptor(sender, **kwargs):
            recebidos.append(kwargs)

        saldo_graos_alterado.connect(receptor)
        try:
            with self.captureOnCommitCallbacks(execute=True):
                self.creditar("10", "evento:1")
            self.assertEqual(len(recebidos), 1)
            self.assertEqual(recebidos[0]["nome"], "producao_creditada")
        finally:
            saldo_graos_alterado.disconnect(receptor)


class SaldoGraosApiTests(GraosSaldoBase, APITestCase):
    def setUp(self):
        self.criar_contexto()
        self.client.force_authenticate(self.usuario)

    def test_rotas_exigem_autenticacao(self):
        self.client.force_authenticate(None)
        for url in ("/api/graos/saldos/", "/api/graos/reservas/", "/api/graos/origens-saldo/"):
            self.assertEqual(self.client.get(url).status_code, 401)

    def test_fluxo_http_padronizado_e_idempotente(self):
        payload = {
            "lote": self.lote.pk,
            "quantidade_kg": "500.000",
            "chave_idempotencia": "api:producao:1",
        }
        primeira = self.client.post(
            "/api/graos/saldos/creditar-producao/",
            payload,
            format="json",
        )
        repetida = self.client.post(
            "/api/graos/saldos/creditar-producao/",
            payload,
            format="json",
        )
        self.assertEqual(primeira.status_code, 201, primeira.data)
        self.assertEqual(repetida.status_code, 200, repetida.data)
        self.assertTrue(primeira.data["sucesso"])
        self.assertFalse(primeira.data["idempotente"])
        self.assertTrue(repetida.data["idempotente"])
        self.assertEqual(primeira.data["codigo"], "producao_creditada")

    def test_endpoints_reserva_consulta_e_origem(self):
        self.creditar("400", "api:credito:reserva")
        resposta = self.client.post(
            "/api/graos/saldos/reservar/",
            {
                "lote": self.lote.pk,
                "quantidade_kg": "125",
                "chave_idempotencia": "api:reserva:1",
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 201, resposta.data)
        posicoes = self.client.get(
            f"/api/graos/saldos/?cad_pro={self.cad_pro.pk}&cultura=soja"
        )
        reservas = self.client.get("/api/graos/reservas/?status=ativa")
        origens = self.client.get("/api/graos/origens-saldo/?tipo=reserva")
        self.assertEqual(posicoes.status_code, 200)
        self.assertEqual(posicoes.data[0]["saldo_disponivel_kg"], "275.000")
        self.assertEqual(len(reservas.data), 1)
        self.assertEqual(len(origens.data), 1)

    def test_painel_consolida_por_cadpro_e_preserva_dimensoes(self):
        self.creditar("400", "painel:credito:a1")
        reservar_saldo(
            usuario=self.usuario,
            lote=self.lote,
            quantidade_kg="100",
            chave_idempotencia="painel:reserva:a1",
        )
        armazem_2 = ArmazemGraos.objects.create(
            propriedade=self.propriedade,
            nome="Silo 2",
            capacidade_kg="2000",
        )
        lote_2 = LoteGraos.objects.create(
            armazem=armazem_2,
            cad_pro=self.cad_pro,
            codigo="SOJA-002",
            cultura="Soja",
            safra="2026/2027",
            classificacao_codigo="PADRAO",
        )
        creditar_producao(
            usuario=self.usuario,
            lote=lote_2,
            quantidade_kg="600",
            chave_idempotencia="painel:credito:a2",
        )
        outro_cadpro = CADPro.objects.create(
            codigo="CAD/002",
            descricao="Segundo produtor",
        )
        CADProPropriedade.objects.create(
            cad_pro=outro_cadpro,
            propriedade=self.propriedade,
        )
        lote_3 = LoteGraos.objects.create(
            armazem=armazem_2,
            cad_pro=outro_cadpro,
            codigo="SOJA-003",
            cultura="Soja",
            safra="2026/2027",
            classificacao_codigo="EXPORTACAO",
        )
        creditar_producao(
            usuario=self.usuario,
            lote=lote_3,
            quantidade_kg="50",
            chave_idempotencia="painel:credito:b1",
        )

        resposta = self.client.get(
            "/api/graos/saldos/painel/",
            {
                "propriedade": self.propriedade.pk,
                "cultura": "soja",
                "safra": "2026/2027",
            },
        )

        self.assertEqual(resposta.status_code, 200, resposta.data)
        self.assertEqual(resposta.data["resumo"]["cadpros"], 2)
        self.assertEqual(resposta.data["resumo"]["posicoes"], 3)
        self.assertEqual(resposta.data["resumo"]["saldo_fisico_kg"], "1050.000")
        self.assertEqual(
            resposta.data["resumo"]["saldo_comprometido_kg"],
            "100.000",
        )
        self.assertEqual(resposta.data["resumo"]["saldo_disponivel_kg"], "950.000")
        consolidado = {
            item["cad_pro"]: item for item in resposta.data["consolidado_cadpro"]
        }
        self.assertEqual(consolidado[str(self.cad_pro.pk)]["posicoes"], 2)
        self.assertEqual(
            consolidado[str(self.cad_pro.pk)]["saldo_fisico_kg"],
            "1000.000",
        )
        self.assertCountEqual(
            [item["armazem"] for item in resposta.data["posicoes"]],
            [self.armazem.pk, armazem_2.pk, armazem_2.pk],
        )

        filtrada = self.client.get(
            "/api/graos/saldos/painel/",
            {
                "cad_pro": outro_cadpro.pk,
                "classificacao_codigo": "exportacao",
                "armazem": armazem_2.pk,
            },
        )
        self.assertEqual(filtrada.status_code, 200, filtrada.data)
        self.assertEqual(filtrada.data["resumo"]["cadpros"], 1)
        self.assertEqual(filtrada.data["resumo"]["saldo_fisico_kg"], "50.000")

    def test_movimentacoes_expoem_rastreabilidade_e_filtro_cadpro(self):
        movimento = self.creditar("25", "painel:rastreabilidade").movimentacoes[0]

        resposta = self.client.get(
            "/api/graos/movimentacoes/",
            {
                "cad_pro": self.cad_pro.pk,
                "operacao": "credito_producao",
                "cultura": self.lote.cultura.lower(),
                "safra": self.lote.safra,
                "classificacao_codigo": "PADRAO",
            },
        )

        self.assertEqual(resposta.status_code, 200, resposta.data)
        self.assertEqual(len(resposta.data), 1)
        self.assertEqual(resposta.data[0]["id"], int(movimento.pk))
        self.assertEqual(resposta.data[0]["cad_pro"], str(self.cad_pro.pk))
        self.assertEqual(resposta.data[0]["cad_pro_codigo"], self.cad_pro.codigo)
        self.assertEqual(resposta.data[0]["cultura"], self.lote.cultura)
        self.assertEqual(resposta.data[0]["safra"], self.lote.safra)
        posicoes = self.client.get(
            "/api/graos/saldos/",
            {"cultura": self.lote.cultura.lower()},
        )
        self.assertEqual(posicoes.status_code, 200, posicoes.data)
        self.assertEqual(len(posicoes.data), 1)
        self.assertEqual(posicoes.data[0]["id"], int(movimento.posicao_id))
        self.assertEqual(
            resposta.data[0]["origem_chave_idempotencia"],
            "painel:rastreabilidade",
        )

    def test_conflito_operacional_tem_contrato_de_erro(self):
        resposta = self.client.post(
            "/api/graos/saldos/reservar/",
            {
                "lote": self.lote.pk,
                "quantidade_kg": "1",
                "chave_idempotencia": "api:sem-saldo",
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 409)
        self.assertFalse(resposta.data["sucesso"])
        self.assertEqual(resposta.data["codigo"], "saldo_insuficiente")

    def test_movimentacoes_continuam_imutaveis(self):
        movimento = self.creditar("10", "api:imutavel").movimentacoes[0]
        url = f"/api/graos/movimentacoes/{movimento.pk}/"
        self.assertEqual(self.client.patch(url, {"quantidade_kg": "20"}).status_code, 405)
        self.assertEqual(self.client.delete(url).status_code, 405)

    def test_reverse_e_resolve_das_quatro_rotas_congeladas(self):
        casos = {
            "graos-producoes-creditar": "/api/graos/producoes/creditar/",
            "graos-ajustes": "/api/graos/ajustes/",
            "movimentacoes-graos-estornar": (
                f"/api/graos/movimentacoes/{self.lote.pk}/estornar/"
            ),
            "graos-transferencias": "/api/graos/transferencias/",
        }
        for alias, caminho in casos.items():
            kwargs = {"pk": self.lote.pk} if "estornar" in alias else {}
            self.assertEqual(reverse(alias, kwargs=kwargs), caminho)
            self.assertEqual(resolve(caminho).view_name, alias)

    def test_quatro_rotas_congeladas_exigem_autenticacao(self):
        self.client.force_authenticate(None)
        for caminho in (
            "/api/graos/producoes/creditar/",
            "/api/graos/ajustes/",
            "/api/graos/movimentacoes/1/estornar/",
            "/api/graos/transferencias/",
        ):
            self.assertEqual(self.client.post(caminho, {}, format="json").status_code, 401)

    def test_sucesso_e_erro_das_quatro_rotas_congeladas(self):
        credito = self.client.post(
            "/api/graos/producoes/creditar/",
            {
                "lote": self.lote.pk,
                "quantidade_kg": "100",
                "chave_idempotencia": "rotas:credito",
            },
            format="json",
        )
        self.assertEqual(credito.status_code, 201, credito.data)
        ajuste = self.client.post(
            "/api/graos/ajustes/",
            {
                "lote": self.lote.pk,
                "delta_fisico_kg": "-10",
                "chave_idempotencia": "rotas:ajuste",
            },
            format="json",
        )
        self.assertEqual(ajuste.status_code, 201, ajuste.data)
        armazem_destino = ArmazemGraos.objects.create(
            propriedade=self.propriedade,
            nome="Silo rotas",
            capacidade_kg="1000",
        )
        lote_destino = LoteGraos.objects.create(
            armazem=armazem_destino,
            cad_pro=self.cad_pro,
            codigo="SOJA-ROTAS",
            cultura="Soja",
            safra="2026/2027",
            classificacao_codigo="PADRAO",
        )
        transferencia = self.client.post(
            "/api/graos/transferencias/",
            {
                "lote_origem": self.lote.pk,
                "lote_destino": lote_destino.pk,
                "quantidade_kg": "10",
                "chave_idempotencia": "rotas:transferencia",
            },
            format="json",
        )
        self.assertEqual(transferencia.status_code, 201, transferencia.data)
        movimento_id = transferencia.data["movimentacoes"][0]["id"]
        estorno = self.client.post(
            f"/api/graos/movimentacoes/{movimento_id}/estornar/",
            {"chave_idempotencia": "rotas:estorno"},
            format="json",
        )
        self.assertEqual(estorno.status_code, 201, estorno.data)

        erros = (
            self.client.post(
                "/api/graos/producoes/creditar/",
                {
                    "lote": self.lote.pk,
                    "quantidade_kg": "5000",
                    "chave_idempotencia": "rotas:credito:erro",
                },
                format="json",
            ),
            self.client.post(
                "/api/graos/ajustes/",
                {
                    "lote": self.lote.pk,
                    "delta_fisico_kg": "0",
                    "chave_idempotencia": "rotas:ajuste:erro",
                },
                format="json",
            ),
            self.client.post(
                "/api/graos/transferencias/",
                {
                    "lote_origem": self.lote.pk,
                    "lote_destino": self.lote.pk,
                    "quantidade_kg": "1",
                    "chave_idempotencia": "rotas:transferencia:erro",
                },
                format="json",
            ),
            self.client.post(
                f"/api/graos/movimentacoes/{estorno.data['movimentacoes'][0]['id']}/estornar/",
                {"chave_idempotencia": "rotas:estorno:erro"},
                format="json",
            ),
        )
        self.assertEqual([item.status_code for item in erros], [409, 400, 409, 409])

    def test_openapi_documenta_quatro_rotas_congeladas(self):
        resposta = self.client.get(
            "/api/schema.json",
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(resposta.status_code, 200)
        caminhos = resposta.json()["paths"]
        for caminho in (
            "/graos/producoes/creditar/",
            "/graos/ajustes/",
            "/graos/movimentacoes/{id}/estornar/",
            "/graos/transferencias/",
        ):
            self.assertIn(caminho, caminhos)
            self.assertIn("post", caminhos[caminho])


class ReversaoMigrationsGraosTests(GraosSaldoBase, TransactionTestCase):
    migrate_from = ("graos", "0001_initial")
    migrate_to = ("graos", "0004_saldos_constraints")

    def test_ciclo_0004_0001_0004_vazio(self):
        executor = MigrationExecutor(connection)
        try:
            executor.migrate([self.migrate_from])
            executor = MigrationExecutor(connection)
            executor.migrate([self.migrate_to])
            estado = executor.loader.project_state([self.migrate_to]).apps
            Posicao = estado.get_model("graos", "PosicaoSaldoGraos")
            self.assertEqual(Posicao.objects.count(), 0)
        finally:
            restaurador = MigrationExecutor(connection)
            restaurador.migrate(restaurador.loader.graph.leaf_nodes())

    def test_ciclo_0004_0001_0004_com_dados_e_reserva(self):
        self.criar_contexto()
        self.creditar("500", "migration:credito")
        reservar_saldo(
            usuario=self.usuario,
            lote=self.lote,
            quantidade_kg="100",
            chave_idempotencia="migration:reserva",
        )
        executor = MigrationExecutor(connection)
        try:
            executor.migrate([self.migrate_from])
            estado_0001 = executor.loader.project_state([self.migrate_from]).apps
            MovimentoLegado = estado_0001.get_model("graos", "MovimentacaoGraos")
            movimentos = list(MovimentoLegado.objects.all())
            self.assertEqual(len(movimentos), 1)
            self.assertEqual(movimentos[0].tipo, "entrada")
            self.assertEqual(movimentos[0].quantidade_kg, Decimal("500.000"))

            executor = MigrationExecutor(connection)
            executor.migrate([self.migrate_to])
            estado_0004 = executor.loader.project_state([self.migrate_to]).apps
            Posicao = estado_0004.get_model("graos", "PosicaoSaldoGraos")
            self.assertEqual(Posicao.objects.get().saldo_fisico_kg, Decimal("500.000"))
        finally:
            restaurador = MigrationExecutor(connection)
            restaurador.migrate(restaurador.loader.graph.leaf_nodes())


@skipUnless(
    connection.vendor == "postgresql",
    "ConcorrÃªncia transacional de saldos requer PostgreSQL.",
)
class ConcorrenciaSaldoGraosPostgreSQLTests(GraosSaldoBase, TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.criar_contexto()
        self.creditar("1000", "concorrencia:credito")

    def _reservar(self, indice):
        close_old_connections()
        try:
            lote = LoteGraos.objects.get(pk=self.lote.pk)
            usuario = get_user_model().objects.get(pk=self.usuario.pk)
            try:
                resultado = reservar_saldo(
                    usuario=usuario,
                    lote=lote,
                    quantidade_kg="700",
                    chave_idempotencia=f"concorrencia:reserva:{indice}",
                )
                return resultado.codigo
            except SaldoGraosInsuficienteError:
                return "saldo_insuficiente"
        finally:
            close_old_connections()

    def test_reservas_concorrentes_nao_superalocam_saldo(self):
        with ThreadPoolExecutor(max_workers=2) as executor:
            resultados = list(executor.map(self._reservar, range(2)))
        self.assertCountEqual(resultados, ["saldo_reservado", "saldo_insuficiente"])
        posicao = PosicaoSaldoGraos.objects.get()
        self.assertEqual(posicao.saldo_comprometido_kg, Decimal("700.000"))
        self.assertEqual(ReservaSaldoGraos.objects.count(), 1)

    def _creditar_concorrente(self, lote_id, chave):
        close_old_connections()
        try:
            lote = LoteGraos.objects.get(pk=lote_id)
            usuario = get_user_model().objects.get(pk=self.usuario.pk)
            try:
                resultado = creditar_producao(
                    usuario=usuario,
                    lote=lote,
                    quantidade_kg="700",
                    chave_idempotencia=chave,
                )
                return resultado.codigo
            except CapacidadeArmazemExcedidaError:
                return "capacidade_excedida"
        finally:
            close_old_connections()

    def test_creditos_concorrentes_em_posicoes_distintas_respeitam_capacidade(self):
        lote_alternativo = LoteGraos.objects.create(
            armazem=self.armazem,
            cad_pro=self.cad_pro,
            codigo="SOJA-ALT",
            cultura="Soja",
            safra="2026/2027",
            classificacao_codigo="EXPORTACAO",
        )
        argumentos = (
            (self.lote.pk, "concorrencia:capacidade:1"),
            (lote_alternativo.pk, "concorrencia:capacidade:2"),
        )
        with ThreadPoolExecutor(max_workers=2) as executor:
            resultados = list(executor.map(lambda args: self._creditar_concorrente(*args), argumentos))
        self.assertCountEqual(
            resultados,
            ["producao_creditada", "capacidade_excedida"],
        )
        total = sum(
            PosicaoSaldoGraos.objects.values_list("saldo_fisico_kg", flat=True),
            Decimal("0.000"),
        )
        self.assertEqual(total, Decimal("1700.000"))

    def _repetir_credito_idempotente(self):
        close_old_connections()
        try:
            resultado = creditar_producao(
                usuario=get_user_model().objects.get(pk=self.usuario.pk),
                lote=LoteGraos.objects.get(pk=self.lote.pk),
                quantidade_kg="100",
                chave_idempotencia="concorrencia:idempotente",
            )
            return resultado.idempotente
        finally:
            close_old_connections()

    def test_mesma_chave_concorrente_cria_um_unico_lancamento(self):
        with ThreadPoolExecutor(max_workers=2) as executor:
            resultados = list(executor.map(lambda _: self._repetir_credito_idempotente(), range(2)))
        self.assertCountEqual(resultados, [False, True])
        origem = OrigemSaldoGraos.objects.get(
            chave_idempotencia="concorrencia:idempotente"
        )
        self.assertEqual(origem.movimentacoes.count(), 1)

    def _executar_corrida(self, chamadas):
        barreira = Barrier(len(chamadas))

        def executar(chamada):
            close_old_connections()
            try:
                barreira.wait(timeout=10)
                try:
                    return "ok", chamada().codigo
                except SaldoGraosError as exc:
                    return "dominio", exc.codigo
                except Exception as exc:  # pragma: no cover - falha diagnÃ³stica
                    return "erro", f"{type(exc).__name__}: {exc}"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=len(chamadas)) as executor:
            futuros = [executor.submit(executar, chamada) for chamada in chamadas]
            return [futuro.result(timeout=20) for futuro in futuros]

    def _assert_invariantes_posicao(self):
        for posicao in PosicaoSaldoGraos.objects.all():
            movimentos = list(posicao.movimentacoes.all())
            self.assertEqual(
                posicao.saldo_fisico_kg,
                sum((item.delta_fisico_kg for item in movimentos), Decimal("0")),
            )
            self.assertEqual(
                posicao.saldo_comprometido_kg,
                sum(
                    (item.delta_comprometido_kg for item in movimentos),
                    Decimal("0"),
                ),
            )
            self.assertGreaterEqual(posicao.saldo_fisico_kg, Decimal("0"))
            self.assertGreaterEqual(posicao.saldo_comprometido_kg, Decimal("0"))
            self.assertLessEqual(
                posicao.saldo_comprometido_kg,
                posicao.saldo_fisico_kg,
            )
            reservado = sum(
                posicao.reservas.values_list("saldo_reservado_kg", flat=True),
                Decimal("0"),
            )
            self.assertEqual(posicao.saldo_comprometido_kg, reservado)

    def test_estorno_concorrente_com_liberacao_sem_deadlock(self):
        reserva = reservar_saldo(
            usuario=self.usuario,
            lote=self.lote,
            quantidade_kg="300",
            chave_idempotencia="corrida:reserva:liberacao",
        )
        movimento_id = reserva.movimentacoes[0].id
        reserva_id = reserva.reserva.id

        def estornar():
            return estornar_movimentacao(
                usuario=get_user_model().objects.get(pk=self.usuario.pk),
                movimentacao=MovimentacaoGraos.objects.get(pk=movimento_id),
                chave_idempotencia="corrida:estorno:liberacao",
            )

        def liberar():
            return liberar_reserva(
                usuario=get_user_model().objects.get(pk=self.usuario.pk),
                reserva=ReservaSaldoGraos.objects.get(pk=reserva_id),
                quantidade_kg="100",
                chave_idempotencia="corrida:liberacao",
            )

        resultados = self._executar_corrida((estornar, liberar))
        self.assertNotIn("erro", {tipo for tipo, _ in resultados}, resultados)
        self.assertEqual(sum(tipo == "ok" for tipo, _ in resultados), 1)
        self._assert_invariantes_posicao()

    def test_estorno_concorrente_com_entrega_sem_deadlock(self):
        reserva = reservar_saldo(
            usuario=self.usuario,
            lote=self.lote,
            quantidade_kg="300",
            chave_idempotencia="corrida:reserva:entrega",
        )
        movimento_id = reserva.movimentacoes[0].id
        reserva_id = reserva.reserva.id

        def estornar():
            return estornar_movimentacao(
                usuario=get_user_model().objects.get(pk=self.usuario.pk),
                movimentacao=MovimentacaoGraos.objects.get(pk=movimento_id),
                chave_idempotencia="corrida:estorno:entrega",
            )

        def entregar():
            return confirmar_entrega(
                usuario=get_user_model().objects.get(pk=self.usuario.pk),
                reserva=ReservaSaldoGraos.objects.get(pk=reserva_id),
                quantidade_kg="100",
                chave_idempotencia="corrida:entrega",
            )

        resultados = self._executar_corrida((estornar, entregar))
        self.assertNotIn("erro", {tipo for tipo, _ in resultados}, resultados)
        self.assertEqual(sum(tipo == "ok" for tipo, _ in resultados), 1)
        self._assert_invariantes_posicao()

    def test_transferencias_em_sentidos_opostos_sem_deadlock(self):
        armazem_b = ArmazemGraos.objects.create(
            propriedade=self.propriedade,
            nome="Silo concorrente B",
            capacidade_kg="2000",
        )
        lote_b = LoteGraos.objects.create(
            armazem=armazem_b,
            cad_pro=self.cad_pro,
            codigo="SOJA-CONCORRENTE-B",
            cultura="Soja",
            safra="2026/2027",
            classificacao_codigo="PADRAO",
        )
        creditar_producao(
            usuario=self.usuario,
            lote=lote_b,
            quantidade_kg="500",
            chave_idempotencia="corrida:credito:b",
        )

        def transferir(origem_id, destino_id, chave):
            return lambda: transferir_saldo_fisico(
                usuario=get_user_model().objects.get(pk=self.usuario.pk),
                lote_origem=LoteGraos.objects.get(pk=origem_id),
                lote_destino=LoteGraos.objects.get(pk=destino_id),
                quantidade_kg="100",
                chave_idempotencia=chave,
            )

        resultados = self._executar_corrida(
            (
                transferir(self.lote.pk, lote_b.pk, "corrida:a:b"),
                transferir(lote_b.pk, self.lote.pk, "corrida:b:a"),
            )
        )
        self.assertEqual([tipo for tipo, _ in resultados], ["ok", "ok"])
        saldos = {
            item.armazem_id: item.saldo_fisico_kg
            for item in PosicaoSaldoGraos.objects.all()
        }
        self.assertEqual(saldos[self.armazem.pk], Decimal("1000.000"))
        self.assertEqual(saldos[armazem_b.pk], Decimal("500.000"))
        self._assert_invariantes_posicao()

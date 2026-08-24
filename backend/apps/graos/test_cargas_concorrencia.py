from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from threading import Barrier
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.db import close_old_connections, connection
from django.test import TransactionTestCase

from apps.cadpro.models import CADPro, CADProPropriedade
from apps.propriedades.models import Propriedade

from .cargas_services import corrigir_carga_colhida, registrar_carga_colhida
from .models import ArmazemGraos, CargaColhida, MovimentacaoGraos, PosicaoSaldoGraos


@skipUnless(connection.vendor == "postgresql", "Requer bloqueios reais do PostgreSQL.")
class CorrecaoCargaConcorrentePostgreSQLTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.usuario = get_user_model().objects.create_user(
            username="correcao_carga_concorrente",
            password="senha-segura-teste",
        )
        self.contextos = []
        for indice, nome in enumerate(("Norte", "Sul"), start=1):
            propriedade = Propriedade.objects.create(
                nome=f"Fazenda {nome}",
                municipio="Sorriso",
                uf="MT",
                area_hectares="500",
            )
            cad_pro = CADPro.objects.create(
                codigo=f"CAD-CONCORRENTE-{indice}",
                descricao=f"Titular {nome}",
            )
            CADProPropriedade.objects.create(
                cad_pro=cad_pro,
                propriedade=propriedade,
            )
            armazem = ArmazemGraos.objects.create(
                propriedade=propriedade,
                nome=f"Silo {nome}",
                capacidade_kg="100000.000",
            )
            self.contextos.append((propriedade, cad_pro, armazem))

        self.carga_a = self._registrar(
            contexto=self.contextos[0],
            placa="AAA1A11",
        )
        self.carga_b = self._registrar(
            contexto=self.contextos[1],
            placa="BBB2B22",
        )

    def _registrar(self, *, contexto, placa, correcao_de_id=None):
        propriedade, cad_pro, armazem = contexto
        return registrar_carga_colhida(
            usuario=self.usuario,
            propriedade=propriedade,
            cad_pro=cad_pro,
            cultura="Soja",
            safra="2026/2027",
            armazem=armazem,
            data_colheita=date(2026, 8, 20),
            placa=placa,
            peso_bruto_kg="1000.000",
            umidade_percentual="14.00",
            impureza_percentual="0.00",
            defeitos_percentual="0.00",
            local_colheita="Talhão de concorrência",
            talhoes_selecionados=(),
            correcao_de_id=correcao_de_id,
        )

    def _corrigir_para(self, *, carga_id, contexto_ids, placa, barreira):
        close_old_connections()
        try:
            usuario = get_user_model().objects.get(pk=self.usuario.pk)
            propriedade = Propriedade.objects.get(pk=contexto_ids[0])
            cad_pro = CADPro.objects.get(pk=contexto_ids[1])
            armazem = ArmazemGraos.objects.get(pk=contexto_ids[2])
            barreira.wait(timeout=10)
            substituta = corrigir_carga_colhida(
                usuario=usuario,
                carga=CargaColhida.objects.get(pk=carga_id),
                motivo="Correção cruzada concorrente",
                propriedade=propriedade,
                cad_pro=cad_pro,
                cultura="Soja",
                safra="2026/2027",
                armazem=armazem,
                data_colheita=date(2026, 8, 20),
                placa=placa,
                motorista="",
                peso_bruto_kg="1000.000",
                umidade_percentual="14.00",
                impureza_percentual="0.00",
                defeitos_percentual="0.00",
                ph=None,
                destinado_semente=False,
                local_colheita="Talhão de concorrência",
                observacoes="",
                talhoes_selecionados=(),
            )
            return substituta.pk
        finally:
            close_old_connections()

    def test_correcoes_cruzadas_nao_geram_deadlock_e_preservam_saldos(self):
        ids_a = tuple(item.pk for item in self.contextos[0])
        ids_b = tuple(item.pk for item in self.contextos[1])
        barreira = Barrier(2)

        with ThreadPoolExecutor(max_workers=2) as executor:
            futuros = (
                executor.submit(
                    self._corrigir_para,
                    carga_id=self.carga_a.pk,
                    contexto_ids=ids_b,
                    placa=self.carga_a.placa,
                    barreira=barreira,
                ),
                executor.submit(
                    self._corrigir_para,
                    carga_id=self.carga_b.pk,
                    contexto_ids=ids_a,
                    placa=self.carga_b.placa,
                    barreira=barreira,
                ),
            )
            substitutas = [futuro.result(timeout=20) for futuro in futuros]

        self.carga_a.refresh_from_db()
        self.carga_b.refresh_from_db()
        self.assertEqual(self.carga_a.status, CargaColhida.Status.SUBSTITUIDA)
        self.assertEqual(self.carga_b.status, CargaColhida.Status.SUBSTITUIDA)
        self.assertCountEqual(
            list(
                CargaColhida.objects.filter(status=CargaColhida.Status.ATIVA)
                .values_list("pk", flat=True)
            ),
            substitutas,
        )
        self.assertEqual(MovimentacaoGraos.objects.count(), 6)
        self.assertEqual(
            sum(
                PosicaoSaldoGraos.objects.values_list("saldo_fisico_kg", flat=True),
                Decimal("0"),
            ),
            Decimal("2000.000"),
        )
        for posicao in PosicaoSaldoGraos.objects.all():
            self.assertEqual(
                posicao.saldo_fisico_kg,
                sum(
                    posicao.movimentacoes.values_list("delta_fisico_kg", flat=True),
                    Decimal("0"),
                ),
            )
            self.assertGreaterEqual(posicao.saldo_fisico_kg, Decimal("0"))

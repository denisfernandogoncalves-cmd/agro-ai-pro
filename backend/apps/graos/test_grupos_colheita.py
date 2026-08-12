from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Event, get_ident
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import close_old_connections, connection, transaction
from django.db.models import Sum
from django.urls import reverse
from rest_framework import serializers
from rest_framework.test import APITestCase
from django.test import TransactionTestCase

from apps.cadpro.models import CADPro, CADProPropriedade
from apps.cadpro.services import CADProComSaldoError, inativar_cadpro
from .test_cargas_colhidas import CargaColhidaBase
from .cargas_services import registrar_carga_colhida
from .models import (
    ArmazemGraos,
    CargaColhida,
    GrupoColheita,
    LoteGraos,
    MovimentacaoGraos,
    PosicaoSaldoGraos,
)
from .serializers import GrupoColheitaSerializer, LoteGraosSerializer
from .services import (
    _validar_estado_lote,
    SaldoGraosError,
    bloquear_cadpro_para_saldo,
    creditar_producao,
    estornar_movimentacao,
    reconciliar_posicao,
    registrar_ajuste,
    registrar_devolucao,
    transferir_saldo_fisico,
)


class GrupoColheitaApiTests(CargaColhidaBase, APITestCase):
    def setUp(self):
        self.criar_contexto()
        self.client.force_authenticate(self.usuario)
        self.url = reverse("grupos-colheita-list")

    def payload(self, **alteracoes):
        dados = {
            "propriedade": self.propriedade.pk,
            "cad_pro": str(self.cad_pro.pk),
            "armazem_padrao": self.armazem.pk,
            "nome": "Equipe Sul",
            "cultura": "Milho",
            "safra": "2026/2027",
            "observacoes": "Equipe da gleba sul.",
            "tolerancia_umidade_percentual": "14.00",
            "desconto_umidade_por_ponto": "1.000",
            "tolerancia_impureza_percentual": "1.00",
            "desconto_impureza_por_ponto": "1.000",
            "tolerancia_defeitos_percentual": "2.00",
            "desconto_defeitos_por_ponto": "1.000",
        }
        dados.update(alteracoes)
        return dados

    def test_crud_sem_delete_filtros_e_inativacao(self):
        criacao = self.client.post(self.url, self.payload(), format="json")
        self.assertEqual(criacao.status_code, 201, criacao.data)
        grupo_id = criacao.data["id"]
        self.assertEqual(criacao.data["cad_pro"], str(self.cad_pro.pk))
        self.assertEqual(criacao.data["armazem_padrao"], self.armazem.pk)
        self.assertFalse(criacao.data["contexto_congelado"])
        self.assertEqual(criacao.data["observacoes"], "Equipe da gleba sul.")

        edicao = self.client.patch(
            reverse("grupos-colheita-detail", args=(grupo_id,)),
            {"nome": "Equipe Sul Atualizada"},
            format="json",
        )
        self.assertEqual(edicao.status_code, 200, edicao.data)
        filtrada = self.client.get(
            self.url,
            {
                "search": "Atualizada",
                "propriedade": self.propriedade.pk,
                "cad_pro": str(self.cad_pro.pk),
                "cultura": "milho",
                "safra": "2026/2027",
                "ativo": "true",
                "armazem_padrao": self.armazem.pk,
            },
        )
        self.assertEqual(filtrada.status_code, 200)
        self.assertEqual([item["id"] for item in filtrada.data], [grupo_id])
        self.assertEqual(
            self.client.delete(reverse("grupos-colheita-detail", args=(grupo_id,))).status_code,
            405,
        )
        inativada = self.client.post(
            reverse("grupos-colheita-inativar", args=(grupo_id,)),
            {},
            format="json",
        )
        self.assertEqual(inativada.status_code, 200)
        self.assertFalse(inativada.data["ativo"])

    def test_exige_armazenagem_padrao_valida(self):
        sem_armazem = self.client.post(
            self.url,
            self.payload(armazem_padrao=None),
            format="json",
        )
        self.assertEqual(sem_armazem.status_code, 400)
        outra_propriedade = self.propriedade.__class__.objects.create(
            nome="Fazenda Externa",
            municipio="Sorriso",
            uf="MT",
            area_hectares="100",
        )
        outro_armazem = ArmazemGraos.objects.create(
            propriedade=outra_propriedade,
            nome="Silo Externo",
            capacidade_kg="1000",
        )
        invalida = self.client.post(
            self.url,
            self.payload(armazem_padrao=outro_armazem.pk),
            format="json",
        )
        self.assertEqual(invalida.status_code, 400)
        self.assertIn("armazem_padrao", invalida.data)

    def test_contexto_congela_apos_carga_e_nome_permanece_editavel(self):
        registrar_carga_colhida(usuario=self.usuario, **self.dados_carga())
        detalhe = reverse("grupos-colheita-detail", args=(self.grupo.pk,))
        bloqueada = self.client.patch(
            detalhe,
            {"cultura": "Milho"},
            format="json",
        )
        self.assertEqual(bloqueada.status_code, 400, bloqueada.data)
        self.assertTrue(GrupoColheita.objects.get(pk=self.grupo.pk).cargas.exists())
        permitida = self.client.patch(
            detalhe,
            {"nome": "Equipe Norte Renomeada"},
            format="json",
        )
        self.assertEqual(permitida.status_code, 200, permitida.data)
        self.assertTrue(permitida.data["contexto_congelado"])

        observacoes = self.client.patch(
            detalhe,
            {"observacoes": "Atualizada após a carga."},
            format="json",
        )
        self.assertEqual(observacoes.status_code, 200, observacoes.data)
        self.assertEqual(observacoes.data["observacoes"], "Atualizada após a carga.")

        self.grupo.refresh_from_db()
        self.grupo.safra = "2027/2028"
        with self.assertRaises(ValidationError):
            self.grupo.save()

    def test_carga_usa_armazem_padrao_e_serializa_uuid(self):
        payload = self.dados_carga()
        payload.pop("armazem")
        carga = registrar_carga_colhida(usuario=self.usuario, **payload)
        self.assertEqual(carga.armazem, self.armazem)
        resposta = self.client.get(reverse("cargas-colhidas-detail", args=(carga.pk,)))
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.data["cad_pro"], str(self.cad_pro.pk))

    def test_carga_rejeita_grupo_inativo_e_cadpro_com_saldo_nao_inativa(self):
        registrar_carga_colhida(usuario=self.usuario, **self.dados_carga())
        resposta = self.client.post(
            f"/api/cadpros/{self.cad_pro.pk}/inativar/",
            {},
            format="json",
        )
        self.assertEqual(resposta.status_code, 409, resposta.data)
        self.cad_pro.refresh_from_db()
        self.assertTrue(self.cad_pro.ativo)

        self.grupo.ativo = False
        self.grupo.save()
        payload = self.dados_carga()
        payload["placa"] = "XYZ9A99"
        with self.assertRaisesMessage(ValueError, "inativo"):
            registrar_carga_colhida(usuario=self.usuario, **payload)
        self.assertEqual(CargaColhida.objects.count(), 1)


@skipUnless(
    connection.vendor == "postgresql",
    "Concorrência transacional de grupos requer PostgreSQL.",
)
class GrupoColheitaConcorrenciaPostgreSQLTests(CargaColhidaBase, TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.criar_contexto()

    def test_primeira_carga_impede_patch_estrutural_ja_validado(self):
        grupo_bloqueado = Event()
        patch_validado = Event()
        dados_carga = self.dados_carga()

        def registrar_primeira_carga():
            close_old_connections()
            try:
                with transaction.atomic():
                    grupo = GrupoColheita.objects.select_for_update().get(pk=self.grupo.pk)
                    grupo_bloqueado.set()
                    if not patch_validado.wait(10):
                        raise AssertionError("O PATCH não chegou à validação.")
                    dados = {**dados_carga, "grupo_colheita": grupo}
                    usuario = get_user_model().objects.get(pk=self.usuario.pk)
                    registrar_carga_colhida(usuario=usuario, **dados)
                return "carga_criada"
            finally:
                close_old_connections()

        def alterar_safra():
            close_old_connections()
            try:
                if not grupo_bloqueado.wait(10):
                    raise AssertionError("A carga não bloqueou o grupo.")
                grupo = GrupoColheita.objects.get(pk=self.grupo.pk)
                serializer = GrupoColheitaSerializer(
                    grupo,
                    data={"safra": "2027/2028"},
                    partial=True,
                )
                serializer.is_valid(raise_exception=True)
                patch_validado.set()
                try:
                    serializer.save()
                except serializers.ValidationError:
                    return "patch_bloqueado"
                return "patch_aplicado"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            carga = executor.submit(registrar_primeira_carga)
            patch = executor.submit(alterar_safra)
            self.assertEqual(carga.result(timeout=20), "carga_criada")
            self.assertEqual(patch.result(timeout=20), "patch_bloqueado")

        self.grupo.refresh_from_db()
        self.assertEqual(self.grupo.safra, "2026/2027")
        self.assertEqual(CargaColhida.objects.filter(grupo_colheita=self.grupo).count(), 1)

    def _criar_lote_saldo(self, *, cad_pro=None, codigo="CONCORRENCIA-CADPRO"):
        return LoteGraos.objects.create(
            armazem=self.armazem,
            cad_pro=cad_pro or self.cad_pro,
            codigo=codigo,
            cultura=self.grupo.cultura,
            safra=self.grupo.safra,
            classificacao_codigo="PADRAO",
        )

    def _concorrer_aumento_com_inativacao(self, operacao, *, cad_pro=None):
        cad_pro = cad_pro or self.cad_pro
        cadpro_bloqueado = Event()
        inativacao_tentando_lock = Event()
        operacao_ident = [None]
        inativacao_ident = [None]
        lock_real = bloquear_cadpro_para_saldo

        def lock_observado(cad_pro_id):
            if get_ident() == inativacao_ident[0]:
                inativacao_tentando_lock.set()
            bloqueado = lock_real(cad_pro_id)
            if (
                get_ident() == operacao_ident[0]
                and str(cad_pro_id) == str(cad_pro.pk)
                and not cadpro_bloqueado.is_set()
            ):
                cadpro_bloqueado.set()
                if not inativacao_tentando_lock.wait(10):
                    raise AssertionError("A inativação não tentou adquirir o lock.")
            return bloqueado

        def aumentar_saldo():
            close_old_connections()
            try:
                operacao_ident[0] = get_ident()
                operacao()
                return "credito_criado"
            finally:
                close_old_connections()

        def inativar():
            close_old_connections()
            try:
                if not cadpro_bloqueado.wait(10):
                    raise AssertionError("A operação não bloqueou o CAD/PRO.")
                inativacao_ident[0] = get_ident()
                try:
                    inativar_cadpro(cad_pro.pk)
                except CADProComSaldoError:
                    return "inativacao_bloqueada"
                return "cadpro_inativado"
            finally:
                close_old_connections()

        with patch(
            "apps.graos.services.bloquear_cadpro_para_saldo",
            side_effect=lock_observado,
        ):
            with ThreadPoolExecutor(max_workers=2) as executor:
                credito = executor.submit(aumentar_saldo)
                inativacao = executor.submit(inativar)
                self.assertEqual(credito.result(timeout=20), "credito_criado")
                self.assertEqual(inativacao.result(timeout=20), "inativacao_bloqueada")

        cad_pro.refresh_from_db()
        self.assertTrue(cad_pro.ativo)
        self.assertEqual(
            PosicaoSaldoGraos.objects.filter(cad_pro=cad_pro).aggregate(
                total=Sum("saldo_fisico_kg")
            )["total"],
            Decimal("100.000"),
        )

    def test_inativacao_concorre_com_credito_sem_lock_artificial(self):
        lote = self._criar_lote_saldo(codigo="LOCK-CREDITO")

        def operacao():
            creditar_producao(
                usuario=get_user_model().objects.get(pk=self.usuario.pk),
                lote=LoteGraos.objects.get(pk=lote.pk),
                quantidade_kg="100",
                chave_idempotencia="concorrencia:cadpro:credito",
            )

        self._concorrer_aumento_com_inativacao(operacao)

    def test_inativacao_concorre_com_devolucao_sem_lock_artificial(self):
        lote = self._criar_lote_saldo(codigo="LOCK-DEVOLUCAO")

        def operacao():
            registrar_devolucao(
                usuario=get_user_model().objects.get(pk=self.usuario.pk),
                lote=LoteGraos.objects.get(pk=lote.pk),
                quantidade_kg="100",
                chave_idempotencia="concorrencia:cadpro:devolucao",
            )

        self._concorrer_aumento_com_inativacao(operacao)

    def test_inativacao_concorre_com_ajuste_positivo_sem_lock_artificial(self):
        lote = self._criar_lote_saldo(codigo="LOCK-AJUSTE")

        def operacao():
            registrar_ajuste(
                usuario=get_user_model().objects.get(pk=self.usuario.pk),
                lote=LoteGraos.objects.get(pk=lote.pk),
                delta_fisico_kg="100",
                chave_idempotencia="concorrencia:cadpro:ajuste",
            )

        self._concorrer_aumento_com_inativacao(operacao)

    def test_inativacao_concorre_com_transferencia_entrada_sem_lock_artificial(self):
        destino = self._criar_lote_saldo(codigo="LOCK-TRANSFERENCIA-DESTINO")
        cad_pro_origem = CADPro.objects.create(
            codigo="LOCK-ORIGEM",
            descricao="Origem da transferência concorrente",
        )
        CADProPropriedade.objects.create(
            cad_pro=cad_pro_origem,
            propriedade=self.propriedade,
        )
        origem = self._criar_lote_saldo(
            cad_pro=cad_pro_origem,
            codigo="LOCK-TRANSFERENCIA-ORIGEM",
        )
        creditar_producao(
            usuario=self.usuario,
            lote=origem,
            quantidade_kg="100",
            chave_idempotencia="concorrencia:transferencia:preparo",
        )

        def operacao():
            transferir_saldo_fisico(
                usuario=get_user_model().objects.get(pk=self.usuario.pk),
                lote_origem=LoteGraos.objects.get(pk=origem.pk),
                lote_destino=LoteGraos.objects.get(pk=destino.pk),
                quantidade_kg="100",
                chave_idempotencia="concorrencia:cadpro:transferencia",
            )

        self._concorrer_aumento_com_inativacao(operacao)

    def test_inativacao_concorre_com_estorno_que_recompoe_saldo(self):
        lote = self._criar_lote_saldo(codigo="LOCK-ESTORNO")
        creditar_producao(
            usuario=self.usuario,
            lote=lote,
            quantidade_kg="100",
            chave_idempotencia="concorrencia:estorno:credito",
        )
        ajuste = registrar_ajuste(
            usuario=self.usuario,
            lote=lote,
            delta_fisico_kg="-100",
            chave_idempotencia="concorrencia:estorno:saida",
        )
        movimento_id = ajuste.movimentacoes[0].id

        def operacao():
            estornar_movimentacao(
                usuario=get_user_model().objects.get(pk=self.usuario.pk),
                movimentacao=MovimentacaoGraos.objects.get(pk=movimento_id),
                chave_idempotencia="concorrencia:cadpro:estorno",
            )

        self._concorrer_aumento_com_inativacao(operacao)

    def test_inativacao_concorre_com_reconciliacao_que_eleva_saldo(self):
        lote = self._criar_lote_saldo(codigo="LOCK-RECONCILIACAO")
        credito = creditar_producao(
            usuario=self.usuario,
            lote=lote,
            quantidade_kg="100",
            chave_idempotencia="concorrencia:reconciliacao:credito",
        )
        posicao_id = credito.posicoes[0].id
        PosicaoSaldoGraos.objects.filter(pk=posicao_id).update(saldo_fisico_kg=0)

        def operacao():
            reconciliar_posicao(
                usuario=get_user_model().objects.get(pk=self.usuario.pk),
                posicao=PosicaoSaldoGraos.objects.get(pk=posicao_id),
                chave_idempotencia="concorrencia:cadpro:reconciliacao",
            )

        self._concorrer_aumento_com_inativacao(operacao)

    def _assert_saldos_cadpro_zerados(self, *cad_pros):
        for cad_pro in cad_pros:
            total = PosicaoSaldoGraos.objects.filter(cad_pro=cad_pro).aggregate(
                total=Sum("saldo_fisico_kg")
            )["total"]
            self.assertEqual(total or Decimal("0.000"), Decimal("0.000"))

    def _preparar_lote_obsoleto(self, *, codigo_lote, codigo_cadpro):
        lote = self._criar_lote_saldo(codigo=codigo_lote)
        lote_recebido = LoteGraos.objects.get(pk=lote.pk)
        cad_pro_destino = CADPro.objects.create(
            codigo=codigo_cadpro,
            descricao="CAD/PRO autoritativo do lote",
        )
        CADProPropriedade.objects.create(
            cad_pro=cad_pro_destino,
            propriedade=self.propriedade,
        )
        LoteGraos.objects.filter(pk=lote.pk).update(cad_pro=cad_pro_destino)
        return lote_recebido, cad_pro_destino

    def test_credito_rejeita_lote_obsoleto_apos_troca_de_cadpro(self):
        lote_recebido, cad_pro_destino = self._preparar_lote_obsoleto(
            codigo_lote="LOTE-OBSOLETO-CREDITO",
            codigo_cadpro="CADPRO-DESTINO-CREDITO",
        )

        with patch("apps.graos.services.bloquear_cadpro_para_saldo") as bloquear:
            with self.assertRaisesMessage(SaldoGraosError, "mudou desde a leitura"):
                creditar_producao(
                    usuario=self.usuario,
                    lote=lote_recebido,
                    quantidade_kg="100",
                    chave_idempotencia="lote-obsoleto:credito",
                )
            bloquear.assert_not_called()

        self.assertEqual(MovimentacaoGraos.objects.count(), 0)
        self._assert_saldos_cadpro_zerados(self.cad_pro, cad_pro_destino)

    def test_ajuste_positivo_rejeita_lote_obsoleto_apos_troca_de_cadpro(self):
        lote_recebido, cad_pro_destino = self._preparar_lote_obsoleto(
            codigo_lote="LOTE-OBSOLETO-AJUSTE",
            codigo_cadpro="CADPRO-DESTINO-AJUSTE",
        )

        with patch("apps.graos.services.bloquear_cadpro_para_saldo") as bloquear:
            with self.assertRaisesMessage(SaldoGraosError, "mudou desde a leitura"):
                registrar_ajuste(
                    usuario=self.usuario,
                    lote=lote_recebido,
                    delta_fisico_kg="100",
                    chave_idempotencia="lote-obsoleto:ajuste",
                )
            bloquear.assert_not_called()

        self.assertEqual(MovimentacaoGraos.objects.count(), 0)
        self._assert_saldos_cadpro_zerados(self.cad_pro, cad_pro_destino)

    def test_devolucao_rejeita_troca_validada_enquanto_lote_esta_bloqueado(self):
        lote = self._criar_lote_saldo(codigo="LOCK-LOTE-DEVOLUCAO")
        cad_pro_alternativo = CADPro.objects.create(
            codigo="LOCK-CADPRO-ALTERNATIVO",
            descricao="CAD/PRO alternativo concorrente",
        )
        CADProPropriedade.objects.create(
            cad_pro=cad_pro_alternativo,
            propriedade=self.propriedade,
        )
        patch_validado = Event()
        lote_bloqueado = Event()
        patch_salvando = Event()
        inativacao_tentando_lock = Event()
        operacao_ident = [None]
        inativacao_ident = [None]
        locks_operacao = []
        lock_real = bloquear_cadpro_para_saldo
        validar_real = _validar_estado_lote

        def lock_observado(cad_pro_id):
            if get_ident() == inativacao_ident[0]:
                inativacao_tentando_lock.set()
            bloqueado = lock_real(cad_pro_id)
            if get_ident() == operacao_ident[0]:
                locks_operacao.append(bloqueado.pk)
            return bloqueado

        def validacao_observada(lote_autoritativo):
            validado = validar_real(lote_autoritativo)
            if get_ident() == operacao_ident[0]:
                lote_bloqueado.set()
                if not patch_salvando.wait(10):
                    raise AssertionError("O PATCH não tentou salvar o lote.")
                if not inativacao_tentando_lock.wait(10):
                    raise AssertionError("A inativação não tentou adquirir o lock.")
            return validado

        def alterar_cadpro():
            close_old_connections()
            try:
                serializer = LoteGraosSerializer(
                    LoteGraos.objects.get(pk=lote.pk),
                    data={"cad_pro": cad_pro_alternativo.pk},
                    partial=True,
                )
                serializer.is_valid(raise_exception=True)
                patch_validado.set()
                if not lote_bloqueado.wait(10):
                    raise AssertionError("A devolução não bloqueou o lote.")
                patch_salvando.set()
                try:
                    serializer.save()
                except serializers.ValidationError:
                    return "patch_rejeitado"
                return "patch_aplicado"
            finally:
                close_old_connections()

        def devolver():
            close_old_connections()
            try:
                if not patch_validado.wait(10):
                    raise AssertionError("O PATCH não foi validado.")
                operacao_ident[0] = get_ident()
                registrar_devolucao(
                    usuario=get_user_model().objects.get(pk=self.usuario.pk),
                    lote=LoteGraos.objects.get(pk=lote.pk),
                    quantidade_kg="100",
                    chave_idempotencia="concorrencia:cadpro:lote:devolucao",
                )
                return "devolucao_criada"
            finally:
                close_old_connections()

        def inativar_atual():
            close_old_connections()
            try:
                if not lote_bloqueado.wait(10):
                    raise AssertionError("A devolução não bloqueou o lote.")
                inativacao_ident[0] = get_ident()
                try:
                    inativar_cadpro(self.cad_pro.pk)
                except CADProComSaldoError:
                    return "inativacao_bloqueada"
                return "cadpro_inativado"
            finally:
                close_old_connections()

        with patch(
            "apps.graos.services.bloquear_cadpro_para_saldo",
            side_effect=lock_observado,
        ), patch(
            "apps.graos.services._validar_estado_lote",
            side_effect=validacao_observada,
        ):
            with ThreadPoolExecutor(max_workers=3) as executor:
                alteracao = executor.submit(alterar_cadpro)
                devolucao = executor.submit(devolver)
                inativacao = executor.submit(inativar_atual)
                self.assertEqual(devolucao.result(timeout=20), "devolucao_criada")
                self.assertEqual(alteracao.result(timeout=20), "patch_rejeitado")
                self.assertEqual(
                    inativacao.result(timeout=20),
                    "inativacao_bloqueada",
                )

        lote.refresh_from_db()
        self.cad_pro.refresh_from_db()
        cad_pro_alternativo.refresh_from_db()
        self.assertEqual(lote.cad_pro_id, self.cad_pro.pk)
        self.assertEqual(locks_operacao, [self.cad_pro.pk])
        self.assertTrue(self.cad_pro.ativo)
        self.assertTrue(cad_pro_alternativo.ativo)
        self.assertEqual(
            PosicaoSaldoGraos.objects.get(cad_pro=self.cad_pro).saldo_fisico_kg,
            Decimal("100.000"),
        )
        self.assertFalse(
            PosicaoSaldoGraos.objects.filter(cad_pro=cad_pro_alternativo).exists()
        )

from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import close_old_connections, connection, transaction
from django.urls import reverse
from rest_framework import serializers
from rest_framework.test import APITestCase
from django.test import TransactionTestCase

from apps.cadpro.services import CADProComSaldoError, inativar_cadpro
from .test_cargas_colhidas import CargaColhidaBase
from .cargas_services import registrar_carga_colhida
from .models import (
    ArmazemGraos,
    CargaColhida,
    GrupoColheita,
    LoteGraos,
    PosicaoSaldoGraos,
)
from .serializers import GrupoColheitaSerializer
from .services import bloquear_cadpro_para_saldo, creditar_producao


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

    def test_credito_e_inativacao_compartilham_lock_do_cadpro(self):
        lote = LoteGraos.objects.create(
            armazem=self.armazem,
            cad_pro=self.cad_pro,
            codigo="CONCORRENCIA-CADPRO",
            cultura=self.grupo.cultura,
            safra=self.grupo.safra,
            classificacao_codigo="PADRAO",
        )
        cadpro_bloqueado = Event()
        inativacao_iniciada = Event()

        def creditar():
            close_old_connections()
            try:
                with transaction.atomic():
                    bloquear_cadpro_para_saldo(self.cad_pro.pk)
                    cadpro_bloqueado.set()
                    if not inativacao_iniciada.wait(10):
                        raise AssertionError("A inativação não foi iniciada.")
                    usuario = get_user_model().objects.get(pk=self.usuario.pk)
                    lote_bloqueado = LoteGraos.objects.get(pk=lote.pk)
                    creditar_producao(
                        usuario=usuario,
                        lote=lote_bloqueado,
                        quantidade_kg="100",
                        chave_idempotencia="concorrencia:cadpro:credito",
                    )
                return "credito_criado"
            finally:
                close_old_connections()

        def inativar():
            close_old_connections()
            try:
                if not cadpro_bloqueado.wait(10):
                    raise AssertionError("O crédito não bloqueou o CAD/PRO.")
                inativacao_iniciada.set()
                try:
                    inativar_cadpro(self.cad_pro.pk)
                except CADProComSaldoError:
                    return "inativacao_bloqueada"
                return "cadpro_inativado"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            credito = executor.submit(creditar)
            inativacao = executor.submit(inativar)
            self.assertEqual(credito.result(timeout=20), "credito_criado")
            self.assertEqual(inativacao.result(timeout=20), "inativacao_bloqueada")

        self.cad_pro.refresh_from_db()
        self.assertTrue(self.cad_pro.ativo)
        self.assertEqual(
            PosicaoSaldoGraos.objects.get(cad_pro=self.cad_pro).saldo_fisico_kg,
            100,
        )

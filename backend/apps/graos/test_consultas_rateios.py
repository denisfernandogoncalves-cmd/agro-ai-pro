from decimal import Decimal
from unittest.mock import patch

from django.urls import reverse
from rest_framework.test import APITestCase

from apps.cadpro.models import CADPro, CADProPropriedade
from apps.propriedades.models import Propriedade
from apps.relatorios.selectors import _item_movimento

from .cargas_services import (
    cancelar_carga_colhida,
    corrigir_carga_colhida,
    registrar_carga_colhida,
)
from .models import MovimentacaoGraos
from .selectors import selecionar_movimentacoes_saldo
from .test_cargas_colhidas import CargaColhidaBase


class ConsultaRateiosTests(CargaColhidaBase, APITestCase):
    def setUp(self):
        self.criar_contexto()
        self.client.force_authenticate(self.usuario)
        self.outra = Propriedade.objects.create(
            nome="Fazenda Associada", municipio="Sorriso", uf="MT",
            area_hectares="500",
        )
        self.outro_cad = CADPro.objects.create(
            codigo="SECUNDARIO-456", descricao="Titular secundário",
        )
        CADProPropriedade.objects.create(cad_pro=self.outro_cad, propriedade=self.outra)
        # O vínculo atual não deve substituir a escolha gravada no rateio.
        CADProPropriedade.objects.create(cad_pro=self.cad_pro, propriedade=self.outra)
        self.dados = {
            **self.dados_carga(),
            "propriedades_selecionadas": [self.propriedade.pk, self.outra.pk],
            "cadpros_por_propriedade": {
                str(self.propriedade.pk): str(self.cad_pro.pk),
                str(self.outra.pk): str(self.outro_cad.pk),
            },
        }
        self.carga = registrar_carga_colhida(usuario=self.usuario, **self.dados)
        self.url = reverse("cargas-colhidas-list")
        self.relatorio_url = "/api/relatorios/operacionais/"

    def listar(self, **filtros):
        resposta = self.client.get(self.url, filtros)
        self.assertEqual(resposta.status_code, 200, resposta.data)
        return [item["id"] for item in resposta.data]

    def relatorio(self, **filtros):
        resposta = self.client.get(self.relatorio_url, {
            "secao": "rastreabilidade", **filtros,
        })
        self.assertEqual(resposta.status_code, 200, resposta.data)
        return resposta.data

    def test_filtra_propriedade_e_cadpro_secundarios(self):
        for filtros in (
            {"propriedade": self.outra.pk},
            {"cad_pro": str(self.outro_cad.pk)},
            {"propriedade": self.outra.pk, "cad_pro": str(self.outro_cad.pk)},
        ):
            with self.subTest(filtros=filtros):
                self.assertEqual(self.listar(**filtros), [self.carga.pk])

    def test_filtros_combinados_devem_corresponder_a_mesma_parcela(self):
        self.assertEqual(self.listar(
            propriedade=self.outra.pk, cad_pro=str(self.cad_pro.pk),
        ), [])
        self.assertEqual(self.listar(
            propriedade=self.propriedade.pk, cad_pro=str(self.outro_cad.pk),
        ), [])

    def test_busca_secundaria_e_multiplas_correspondencias_sem_duplicar(self):
        for termo in (self.outra.nome, self.outro_cad.codigo, "Fazenda"):
            with self.subTest(termo=termo):
                self.assertEqual(self.listar(search=termo), [self.carga.pk])

    def test_cadpro_compartilhado_nao_duplica_carga_na_listagem(self):
        compartilhada = registrar_carga_colhida(
            usuario=self.usuario,
            **{
                **self.dados,
                "placa": "COM1A23",
                "cadpros_por_propriedade": {
                    str(self.propriedade.pk): str(self.cad_pro.pk),
                    str(self.outra.pk): str(self.cad_pro.pk),
                },
            },
        )
        self.assertEqual(self.listar(
            cad_pro=str(self.cad_pro.pk), search="COM1A23",
        ), [compartilhada.pk])

    def test_relatorio_identifica_cada_parcela_sem_duplicar_peso(self):
        dados = self.relatorio(secao="producao")
        self.assertEqual(dados["dados"]["total"], 2)
        self.assertEqual(dados["totais"]["producao_kg"], "975.000")
        self.assertEqual(sum(
            Decimal(item["quantidade_kg"]) for item in dados["dados"]["resultados"]
        ), Decimal("975.000"))
        for propriedade, cad, quantidade in (
            (self.propriedade, self.cad_pro, "650.000"),
            (self.outra, self.outro_cad, "325.000"),
        ):
            with self.subTest(propriedade=propriedade.pk):
                filtrado = self.relatorio(propriedade=propriedade.pk, cad_pro=str(cad.pk))
                self.assertEqual(filtrado["dados"]["total"], 1)
                item = filtrado["dados"]["resultados"][0]
                self.assertEqual(item["carga_colhida"], self.carga.pk)
                self.assertEqual(item["carga_status"], "ativa")
                self.assertEqual(item["propriedade"], propriedade.pk)
                self.assertEqual(item["propriedade_nome"], propriedade.nome)
                self.assertEqual(item["cad_pro"], str(cad.pk))
                self.assertEqual(item["cad_pro_codigo"], cad.codigo)
                self.assertEqual(item["quantidade_kg"], quantidade)
                self.assertEqual(item["placa_carga"], "ABC1D23")
                self.assertEqual(item["posicao"]["propriedade"], propriedade.pk)

    def test_estorno_secundario_preserva_rastro_e_paginacao(self):
        cancelar_carga_colhida(usuario=self.usuario, carga=self.carga)
        self.assertEqual(self.listar(propriedade=self.outra.pk, status="cancelada"), [self.carga.pk])
        self.assertEqual(self.listar(propriedade=self.outra.pk, status="ativa"), [])
        ids = set()
        for pagina in (1, 2):
            dados = self.relatorio(propriedade=self.outra.pk, pagina=pagina, por_pagina=1)
            self.assertEqual(dados["dados"]["total"], 2)
            item = dados["dados"]["resultados"][0]
            ids.add(item["id"])
            self.assertEqual(item["carga_colhida"], self.carga.pk)
            self.assertEqual(item["carga_status"], "cancelada")
            self.assertEqual(item["propriedade"], self.outra.pk)
            self.assertEqual(item["cad_pro"], str(self.outro_cad.pk))
            self.assertEqual(item["placa_carga"], "ABC1D23")
        self.assertEqual(len(ids), 2)
        self.assertEqual(self.relatorio(secao="producao")["dados"]["total"], 0)

    def test_correcao_distingue_carga_antiga_e_substituta(self):
        substituta = corrigir_carga_colhida(
            usuario=self.usuario, carga=self.carga,
            **{**self.dados, "peso_bruto_kg": "2000"},
        )
        dados = self.relatorio(propriedade=self.outra.pk)
        self.assertEqual(dados["dados"]["total"], 3)
        for item in dados["dados"]["resultados"]:
            self.assertEqual(item["propriedade"], self.outra.pk)
            self.assertEqual(item["cad_pro"], str(self.outro_cad.pk))
            self.assertIn(item["carga_colhida"], (self.carga.pk, substituta.pk))
            self.assertEqual(item["carga_status"], (
                "ativa" if item["carga_colhida"] == substituta.pk else "substituida"
            ))
        producao = self.relatorio(secao="producao", propriedade=self.outra.pk)
        self.assertEqual(producao["dados"]["total"], 1)
        self.assertEqual(producao["dados"]["resultados"][0]["carga_colhida"], substituta.pk)
        self.assertEqual(producao["totais"]["producao_kg"], "650.000")

    def test_legado_sem_rateio_mantem_filtro_e_rastreabilidade(self):
        # Fixture do formato anterior à migration 0011, sem apagar dados.
        with patch("apps.graos.cargas_services.RateioCargaColhida.objects.create"):
            legado = registrar_carga_colhida(
                usuario=self.usuario,
                **{**self.dados_carga(), "placa": "LEG1A23"},
            )
        self.assertFalse(legado.rateios.exists())
        self.assertEqual(self.listar(
            propriedade=self.propriedade.pk, cad_pro=str(self.cad_pro.pk), search="LEG1A23",
        ), [legado.pk])
        cancelar_carga_colhida(usuario=self.usuario, carga=legado)
        itens = [item for item in self.relatorio()["dados"]["resultados"]
                 if item["carga_colhida"] == legado.pk]
        self.assertEqual(len(itens), 2)
        self.assertTrue(all(item["propriedade"] == self.propriedade.pk for item in itens))
        self.assertTrue(all(item["carga_status"] == "cancelada" for item in itens))

    def test_contexto_do_rateio_e_carregado_sem_consultas_por_linha(self):
        cancelar_carga_colhida(usuario=self.usuario, carga=self.carga)
        total_movimentos = MovimentacaoGraos.objects.count()
        with self.assertNumQueries(1):
            itens = [_item_movimento(item) for item in selecionar_movimentacoes_saldo()]
        self.assertEqual(len(itens), total_movimentos)
        self.assertTrue(all(item["carga_colhida"] == self.carga.pk for item in itens))

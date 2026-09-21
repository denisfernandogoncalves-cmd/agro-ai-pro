from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APITestCase

from apps.cadpro.models import CADPro, CADProPropriedade
from apps.graos.cargas_services import registrar_carga_colhida
from apps.graos.models import (
    ArmazemGraos,
    GrupoColheita,
    LoteGraos,
    MovimentacaoGraos,
)
from apps.graos.services import creditar_producao, reservar_saldo
from apps.propriedades.models import Propriedade
from apps.vendas.services import confirmar_venda, criar_rascunho, registrar_entrega_venda

from .selectors import selecionar_relatorio_operacional


class RelatorioOperacionalBase:
    def criar_cenario(self):
        self.usuario = get_user_model().objects.create_user("relatorio-op", password="x")
        self.propriedade_a = Propriedade.objects.create(
            nome="Fazenda A", municipio="Sorriso", uf="MT", area_hectares="100"
        )
        self.propriedade_b = Propriedade.objects.create(
            nome="Fazenda B", municipio="Sinop", uf="MT", area_hectares="80"
        )
        self.propriedade_c = Propriedade.objects.create(
            nome="Fazenda C", municipio="Cascavel", uf="PR", area_hectares="70"
        )
        self.cad_a = CADPro.objects.create(codigo="CAD-A", descricao="Titular A")
        self.cad_b = CADPro.objects.create(codigo="CAD-B", descricao="Titular B")
        for propriedade in (self.propriedade_a, self.propriedade_b):
            CADProPropriedade.objects.create(cad_pro=self.cad_a, propriedade=propriedade)
        CADProPropriedade.objects.create(cad_pro=self.cad_b, propriedade=self.propriedade_c)
        self.armazem_a = ArmazemGraos.objects.create(
            propriedade=self.propriedade_a, nome="Silo A", capacidade_kg="100000"
        )
        self.armazem_b = ArmazemGraos.objects.create(
            propriedade=self.propriedade_b, nome="Silo B", capacidade_kg="100000"
        )
        self.armazem_c = ArmazemGraos.objects.create(
            propriedade=self.propriedade_c, nome="Silo C", capacidade_kg="100000"
        )
        self.lote_a = self._lote(self.armazem_a, self.cad_a, "A", "Soja", "2026/2027", "PADRAO")
        self.lote_b = self._lote(self.armazem_b, self.cad_a, "B", "Milho", "2026/2027", "SEMENTE")
        self.lote_c = self._lote(self.armazem_c, self.cad_b, "C", "Soja", "2025/2026", "PADRAO")
        self._credito(self.lote_a, "1000", "credito:a", date(2026, 8, 1))
        self._credito(self.lote_b, "2000", "credito:b", date(2026, 8, 2))
        self._credito(self.lote_c, "3000", "credito:c", date(2026, 7, 1))
        reservar_saldo(
            usuario=self.usuario,
            lote=self.lote_a,
            quantidade_kg="250",
            chave_idempotencia="reserva:a",
            referencia_externa="RES-A",
        )
        self.venda = criar_rascunho(
            usuario=self.usuario,
            chave_idempotencia="venda:a",
            numero_contrato="VENDA-A",
            cliente_nome="Cliente A",
            posicao=self.lote_a.movimentacoes.first().posicao,
            quantidade_kg="100",
            data_contrato=date(2026, 8, 3),
        )
        confirmar_venda(
            usuario=self.usuario,
            venda=self.venda,
            chave_idempotencia="venda:a:confirmar",
        )
        registrar_entrega_venda(
            usuario=self.usuario,
            venda=self.venda,
            chave_idempotencia="venda:a:entrega",
            quantidade_kg="40",
            data_entrega=date(2026, 8, 4),
        )

    def _lote(self, armazem, cad, codigo, cultura, safra, classificacao):
        return LoteGraos.objects.create(
            armazem=armazem,
            cad_pro=cad,
            codigo=codigo,
            cultura=cultura,
            safra=safra,
            classificacao_codigo=classificacao,
        )

    def _credito(self, lote, quantidade, chave, data_movimento):
        return creditar_producao(
            usuario=self.usuario,
            lote=lote,
            quantidade_kg=quantidade,
            chave_idempotencia=chave,
            data_movimento=data_movimento,
        )

    def relatorio(self, **filtros):
        return selecionar_relatorio_operacional(
            secao=filtros.pop("secao", "saldos"),
            pagina=filtros.pop("pagina", 1),
            por_pagina=filtros.pop("por_pagina", 25),
            **filtros,
        )


class RelatorioOperacionalSelectorTests(RelatorioOperacionalBase, TestCase):
    def setUp(self):
        self.criar_cenario()

    def test_cadpro_com_duas_propriedades_nao_duplica_posicoes(self):
        dados = self.relatorio(cad_pro=self.cad_a.pk)
        self.assertEqual(dados["totais"]["posicoes"], 2)
        self.assertEqual(dados["totais"]["saldo_fisico_kg"], "2960.000")
        self.assertEqual(dados["totais"]["saldo_comprometido_kg"], "310.000")
        self.assertEqual(dados["totais"]["saldo_disponivel_kg"], "2650.000")
        self.assertEqual(len(dados["por_cad_pro"]), 1)
        self.assertEqual(len(dados["por_propriedade"]), 2)

    def test_multiplos_cadpros_e_formula_em_todos_os_niveis(self):
        dados = self.relatorio()
        self.assertEqual(dados["totais"]["saldo_fisico_kg"], "5960.000")
        for item in [dados["totais"], *dados["por_cad_pro"], *dados["por_propriedade"]]:
            self.assertEqual(
                Decimal(item["saldo_disponivel_kg"]),
                Decimal(item["saldo_fisico_kg"]) - Decimal(item["saldo_comprometido_kg"]),
            )

    def test_filtros_dimensionais_isolados_e_combinados(self):
        casos = (
            ({"propriedade": self.propriedade_b.pk}, 1),
            ({"cultura": "milho"}, 1),
            ({"safra": "2025/2026"}, 1),
            ({"classificacao_codigo": "SEMENTE"}, 1),
            ({"armazem": self.armazem_a.pk}, 1),
            ({"cad_pro": self.cad_a.pk, "cultura": "Soja", "safra": "2026/2027", "classificacao_codigo": "PADRAO", "armazem": self.armazem_a.pk}, 1),
            ({"cad_pro": self.cad_b.pk, "cultura": "Milho"}, 0),
        )
        for filtros, esperado in casos:
            with self.subTest(filtros=filtros):
                self.assertEqual(self.relatorio(**filtros)["totais"]["posicoes"], esperado)

    def test_periodo_producao_saldos_reservas_vendas_entregas_historico(self):
        filtros = {"data_inicio": date(2026, 8, 1), "data_fim": date(2026, 8, 31)}
        self.assertEqual(self.relatorio(secao="producao", **filtros)["dados"]["total"], 2)
        self.assertEqual(self.relatorio(secao="reservas", **filtros)["dados"]["total"], 2)
        self.assertEqual(self.relatorio(secao="vendas", **filtros)["dados"]["total"], 1)
        self.assertEqual(self.relatorio(secao="entregas", **filtros)["dados"]["total"], 1)
        historico = self.relatorio(secao="movimentacoes", **filtros)
        self.assertEqual(historico["dados"]["total"], 5)
        self.assertEqual(historico["totais"]["producao_kg"], "3000.000")
        self.assertEqual(historico["totais"]["entregas_kg"], "40.000")

    def test_periodo_entregas_independe_da_data_do_contrato(self):
        venda_julho = criar_rascunho(
            usuario=self.usuario,
            chave_idempotencia="venda:julho",
            numero_contrato="VENDA-JULHO",
            cliente_nome="Cliente Julho",
            posicao=self.lote_a.movimentacoes.first().posicao,
            quantidade_kg="20",
            data_contrato=date(2026, 7, 31),
        )
        confirmar_venda(
            usuario=self.usuario,
            venda=venda_julho,
            chave_idempotencia="venda:julho:confirmar",
        )
        registrar_entrega_venda(
            usuario=self.usuario,
            venda=venda_julho,
            chave_idempotencia="venda:julho:entrega",
            quantidade_kg="20",
            data_entrega=date(2026, 8, 5),
        )

        filtros = {"data_inicio": date(2026, 8, 1), "data_fim": date(2026, 8, 31)}
        entregas = self.relatorio(secao="entregas", **filtros)
        vendas = self.relatorio(secao="vendas", **filtros)

        self.assertEqual(entregas["dados"]["total"], 2)
        self.assertEqual(entregas["totais"]["entregas_kg"], "60.000")
        self.assertEqual(
            {item["numero_contrato"] for item in entregas["dados"]["resultados"]},
            {"VENDA-A", "VENDA-JULHO"},
        )
        self.assertEqual(vendas["dados"]["total"], 1)

    def test_rastreabilidade_expoe_origem_snapshots_carga_grupo_e_placa(self):
        grupo = GrupoColheita.objects.create(
            propriedade=self.propriedade_a,
            cad_pro=self.cad_a,
            armazem_padrao=self.armazem_a,
            nome="Grupo Norte",
            cultura="Soja",
            safra="2026/2027",
            tolerancia_umidade_percentual="13.00",
            desconto_umidade_por_ponto="1.000",
            tolerancia_impureza_percentual="1.00",
            desconto_impureza_por_ponto="0.500",
            tolerancia_defeitos_percentual="2.00",
            desconto_defeitos_por_ponto="2.000",
            criado_por=self.usuario,
        )
        carga = registrar_carga_colhida(
            usuario=self.usuario,
            grupo_colheita=grupo,
            armazem=self.armazem_a,
            data_colheita=date(2026, 8, 9),
            placa="ABC-1D23",
            peso_bruto_kg="1000.000",
            umidade_percentual="14.00",
            impureza_percentual="2.00",
            defeitos_percentual="3.00",
        )

        dados = self.relatorio(
            secao="rastreabilidade",
            armazem=self.armazem_a.pk,
            data_inicio=date(2026, 8, 9),
            data_fim=date(2026, 8, 9),
        )
        item = next(
            resultado
            for resultado in dados["dados"]["resultados"]
            if resultado["carga_colhida"] == carga.pk
        )

        self.assertEqual(item["origem"], carga.movimentacao.origem_id)
        self.assertEqual(item["origem_tipo"], "producao")
        self.assertEqual(item["carga_colhida"], carga.pk)
        self.assertEqual(item["grupo_colheita"], grupo.pk)
        self.assertEqual(item["grupo_colheita_nome"], "Grupo Norte")
        self.assertEqual(item["placa_carga"], "ABC1D23")
        self.assertEqual(
            Decimal(item["snapshot_anterior"]["saldo_disponivel_kg"]),
            Decimal(item["snapshot_anterior"]["saldo_fisico_kg"])
            - Decimal(item["snapshot_anterior"]["saldo_comprometido_kg"]),
        )
        self.assertEqual(
            Decimal(item["snapshot_posterior"]["saldo_disponivel_kg"]),
            Decimal(item["snapshot_posterior"]["saldo_fisico_kg"])
            - Decimal(item["snapshot_posterior"]["saldo_comprometido_kg"]),
        )

    def test_consistencia_com_ledger_e_paginacao(self):
        dados = self.relatorio(secao="movimentacoes", pagina=2, por_pagina=2)
        self.assertEqual(dados["dados"]["pagina"], 2)
        self.assertLessEqual(len(dados["dados"]["resultados"]), 2)
        posicoes = {item["id"]: item for item in self.relatorio()["dados"]["resultados"]}
        for posicao in {item.posicao for item in self.lote_a.movimentacoes.all()}:
            oficial = posicoes[posicao.pk]
            self.assertEqual(Decimal(oficial["saldo_fisico_kg"]), posicao.saldo_fisico_kg)
            self.assertEqual(Decimal(oficial["saldo_comprometido_kg"]), posicao.saldo_comprometido_kg)


class RelatorioOperacionalApiTests(RelatorioOperacionalBase, APITestCase):
    url = "/api/relatorios/operacionais/"

    def setUp(self):
        self.criar_cenario()
        self.client.force_authenticate(self.usuario)

    def test_exige_autenticacao(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(self.url).status_code, 401)

    def test_endpoint_e_opcoes_sao_somente_leitura(self):
        contagens = (
            MovimentacaoGraos.objects.count(),
            self.lote_a.movimentacoes.first().posicao.__class__.objects.count(),
        )
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.assertEqual(self.client.get(f"{self.url}opcoes/").status_code, 200)
        for metodo in (self.client.post, self.client.put, self.client.patch, self.client.delete):
            self.assertEqual(metodo(self.url, {}).status_code, 405)
        self.assertEqual(
            contagens,
            (
                MovimentacaoGraos.objects.count(),
                self.lote_a.movimentacoes.first().posicao.__class__.objects.count(),
            ),
        )

    def test_valida_filtros_e_retorna_secao(self):
        resposta = self.client.get(
            self.url,
            {
                "cad_pro": self.cad_a.pk,
                "propriedade": self.propriedade_a.pk,
                "cultura": "Soja",
                "safra": "2026/2027",
                "classificacao_codigo": "padrao",
                "armazem": self.armazem_a.pk,
                "data_inicio": "2026-08-01",
                "data_fim": "2026-08-31",
                "secao": "rastreabilidade",
            },
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.data["secao"], "rastreabilidade")
        self.assertTrue(resposta.data["dados"]["resultados"])
        self.assertEqual(
            resposta.data["dados"]["resultados"][0]["posicao"]["classificacao_codigo"],
            "PADRAO",
        )
        invalida = self.client.get(
            self.url, {"data_inicio": "2026-09-01", "data_fim": "2026-08-01"}
        )
        self.assertEqual(invalida.status_code, 400)

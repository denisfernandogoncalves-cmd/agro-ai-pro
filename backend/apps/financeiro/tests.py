from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.propriedades.models import Propriedade

from .models import (
    CategoriaFinanceira,
    CentroCusto,
    LancamentoFinanceiro,
    ParceiroFinanceiro,
)
from .services import (
    OperacaoFinanceiraError,
    cancelar_lancamento,
    liquidar_lancamento,
    resumo_financeiro,
)


class FinanceiroRegrasTests(TestCase):
    def setUp(self):
        self.despesa = CategoriaFinanceira.objects.create(
            nome="Insumos",
            aplicacao=CategoriaFinanceira.Aplicacao.DESPESA,
        )
        self.receita = CategoriaFinanceira.objects.create(
            nome="Venda de grãos",
            aplicacao=CategoriaFinanceira.Aplicacao.RECEITA,
        )
        self.lancamento = LancamentoFinanceiro.objects.create(
            tipo=LancamentoFinanceiro.Tipo.PAGAR,
            descricao="Fertilizante",
            valor="1000",
            categoria=self.despesa,
            data_vencimento=timezone.localdate() + timedelta(days=5),
        )

    def test_categoria_deve_ser_compativel_com_tipo(self):
        lancamento = LancamentoFinanceiro(
            tipo=LancamentoFinanceiro.Tipo.PAGAR,
            descricao="Inválido",
            valor="100",
            categoria=self.receita,
            data_vencimento=timezone.localdate(),
        )

        with self.assertRaisesMessage(ValidationError, "categoria de despesa"):
            lancamento.full_clean()

    def test_liquida_lancamento_pendente(self):
        liquidado = liquidar_lancamento(
            self.lancamento,
            data_liquidacao=timezone.localdate(),
            valor_liquidado="980.50",
        )

        self.assertEqual(liquidado.status, LancamentoFinanceiro.Status.LIQUIDADO)
        self.assertEqual(liquidado.valor_liquidado, Decimal("980.50"))

    def test_impede_liquidacao_repetida(self):
        liquidar_lancamento(
            self.lancamento,
            data_liquidacao=timezone.localdate(),
            valor_liquidado="1000",
        )

        with self.assertRaisesMessage(OperacaoFinanceiraError, "pendentes"):
            liquidar_lancamento(
                self.lancamento,
                data_liquidacao=timezone.localdate(),
                valor_liquidado="1000",
            )

    def test_cancela_somente_pendente(self):
        cancelado = cancelar_lancamento(self.lancamento)

        self.assertEqual(cancelado.status, LancamentoFinanceiro.Status.CANCELADO)
        with self.assertRaisesMessage(OperacaoFinanceiraError, "pendentes"):
            cancelar_lancamento(cancelado)

    def test_identifica_lancamento_atrasado(self):
        self.lancamento.data_vencimento = timezone.localdate() - timedelta(days=1)
        self.assertTrue(self.lancamento.atrasado)

    def test_resumo_separa_previsto_realizado_e_atrasado(self):
        self.lancamento.data_vencimento = timezone.localdate() - timedelta(days=1)
        self.lancamento.save(update_fields=("data_vencimento",))
        entrada = LancamentoFinanceiro.objects.create(
            tipo=LancamentoFinanceiro.Tipo.RECEBER,
            descricao="Venda de soja",
            valor="1600",
            categoria=self.receita,
            data_vencimento=timezone.localdate(),
        )
        liquidar_lancamento(
            entrada,
            data_liquidacao=timezone.localdate(),
            valor_liquidado="1500",
        )

        resumo = resumo_financeiro(LancamentoFinanceiro.objects.all())

        self.assertEqual(resumo["a_pagar"], Decimal("1000"))
        self.assertEqual(resumo["entradas_realizadas"], Decimal("1500"))
        self.assertEqual(resumo["valor_atrasado"], Decimal("1000"))


class FinanceiroApiTests(APITestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(
            username="financeiro",
            password="senha-segura",
        )
        self.categoria = CategoriaFinanceira.objects.create(
            nome="Operação",
            aplicacao=CategoriaFinanceira.Aplicacao.DESPESA,
        )
        self.propriedade = Propriedade.objects.create(
            nome="Fazenda Financeira",
            municipio="Sorriso",
            uf="MT",
            area_hectares="100",
        )
        self.parceiro = ParceiroFinanceiro.objects.create(
            nome="Fornecedor Rural",
            tipo=ParceiroFinanceiro.Tipo.FORNECEDOR,
        )
        self.centro = CentroCusto.objects.create(
            nome="Safra soja",
            propriedade=self.propriedade,
            safra="2026/2027",
        )
        self.lancamento = LancamentoFinanceiro.objects.create(
            tipo=LancamentoFinanceiro.Tipo.PAGAR,
            descricao="Defensivos",
            valor="500",
            categoria=self.categoria,
            parceiro=self.parceiro,
            centro_custo=self.centro,
            propriedade=self.propriedade,
            safra="2026/2027",
            data_vencimento=timezone.localdate() + timedelta(days=10),
        )

    def test_endpoints_exigem_autenticacao(self):
        for nome in (
            "categorias-list",
            "parceiros-list",
            "centros-custo-list",
            "lancamentos-list",
        ):
            self.assertEqual(self.client.get(reverse(nome)).status_code, 401)

    def test_cria_cadastros_auxiliares(self):
        self.client.force_authenticate(self.usuario)

        categoria = self.client.post(
            reverse("categorias-list"),
            {"nome": "Combustível", "aplicacao": "despesa", "ativa": True},
        )
        parceiro = self.client.post(
            reverse("parceiros-list"),
            {"nome": "Cliente A", "tipo": "cliente", "ativo": True},
        )

        self.assertEqual(categoria.status_code, 201)
        self.assertEqual(parceiro.status_code, 201)

    def test_cria_e_filtra_lancamento(self):
        self.client.force_authenticate(self.usuario)
        dados = {
            "tipo": "pagar",
            "descricao": "Frete",
            "valor": "250.00",
            "categoria": self.categoria.pk,
            "parceiro": self.parceiro.pk,
            "propriedade": self.propriedade.pk,
            "safra": "2026/2027",
            "data_emissao": timezone.localdate().isoformat(),
            "data_vencimento": (timezone.localdate() + timedelta(days=20)).isoformat(),
        }

        criada = self.client.post(reverse("lancamentos-list"), dados)
        lista = self.client.get(
            reverse("lancamentos-list"),
            {"tipo": "pagar", "search": "Frete"},
        )

        self.assertEqual(criada.status_code, 201)
        self.assertEqual(len(lista.data), 1)

    def test_liquida_por_acao(self):
        self.client.force_authenticate(self.usuario)

        resposta = self.client.post(
            reverse("lancamentos-liquidar", args=[self.lancamento.pk]),
            {
                "data_liquidacao": timezone.localdate().isoformat(),
                "valor_liquidado": "495.00",
            },
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.data["status"], "liquidado")

    def test_rejeita_liquidacao_invalida(self):
        self.client.force_authenticate(self.usuario)

        resposta = self.client.post(
            reverse("lancamentos-liquidar", args=[self.lancamento.pk]),
            {"data_liquidacao": "data-invalida", "valor_liquidado": "0"},
        )

        self.assertEqual(resposta.status_code, 400)

    def test_cancela_por_acao(self):
        self.client.force_authenticate(self.usuario)

        resposta = self.client.post(
            reverse("lancamentos-cancelar", args=[self.lancamento.pk]),
            {},
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.data["status"], "cancelado")

    def test_resumo_financeiro(self):
        self.client.force_authenticate(self.usuario)

        resposta = self.client.get(reverse("lancamentos-resumo"))

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(Decimal(resposta.data["a_pagar"]), Decimal("500"))

    def test_protege_categoria_em_uso(self):
        self.client.force_authenticate(self.usuario)

        resposta = self.client.delete(
            reverse("categorias-detail", args=[self.categoria.pk])
        )

        self.assertEqual(resposta.status_code, 409)


    def test_filtros_periodo_parceiro_situacao_e_resumo(self):
        self.client.force_authenticate(self.usuario)
        self.lancamento.data_vencimento = date(2026, 9, 10)
        self.lancamento.save()
        pago = LancamentoFinanceiro.objects.create(
            tipo="pagar", descricao="Frete pago", valor="200",
            categoria=self.categoria, parceiro=self.parceiro,
            data_vencimento=date(2026, 8, 1), status="liquidado",
            data_liquidacao=date(2026, 9, 10), valor_liquidado="195",
        )
        LancamentoFinanceiro.objects.create(
            tipo="pagar", descricao="Outro parceiro", valor="900",
            categoria=self.categoria, data_vencimento=date(2026, 9, 10),
            status="liquidado", data_liquidacao=date(2026, 9, 10), valor_liquidado="900",
        )
        for params, esperado, campo, total in (
            ({"status": "pendente", "vencimento_inicio": "2026-09-10", "vencimento_fim": "2026-09-10"}, self.lancamento.pk, "a_pagar", "500"),
            ({"status": "liquidado", "liquidacao_inicio": "2026-09-10", "liquidacao_fim": "2026-09-10"}, pago.pk, "saidas_realizadas", "195"),
        ):
            with self.subTest(params=params):
                params.update(tipo="pagar", parceiro=self.parceiro.pk)
                resposta = self.client.get(reverse("lancamentos-list"), params)
                self.assertEqual(resposta.status_code, 200)
                self.assertEqual([item["id"] for item in resposta.data], [esperado])
                resumo = self.client.get(reverse("lancamentos-resumo"), params)
                self.assertEqual(Decimal(resumo.data[campo]), Decimal(total))
        for params in (
            {"liquidacao_inicio": "2026-09-11"},
            {"liquidacao_fim": "2026-09-09"},
            {"search": "inexistente"},
        ):
            self.assertEqual(self.client.get(reverse("lancamentos-list"), params).data, [])
            resumo = self.client.get(reverse("lancamentos-resumo"), params)
            self.assertEqual(Decimal(resumo.data["a_pagar"]), 0)
            self.assertEqual(Decimal(resumo.data["saidas_realizadas"]), 0)

    def test_rejeita_periodos_invalidos_na_lista_e_resumo(self):
        self.client.force_authenticate(self.usuario)
        for endpoint in ("lancamentos-list", "lancamentos-resumo"):
            for prefixo in ("vencimento", "liquidacao"):
                for params in (
                    {f"{prefixo}_inicio": "2026-02-30"},
                    {f"{prefixo}_fim": "invalida"},
                    {f"{prefixo}_inicio": "2026-09-20", f"{prefixo}_fim": "2026-09-01"},
                ):
                    with self.subTest(endpoint=endpoint, params=params):
                        self.assertEqual(self.client.get(reverse(endpoint), params).status_code, 400)


    def test_filtro_recebedor_nome_livre_ou_parceiro(self):
        self.client.force_authenticate(self.usuario)
        livre = LancamentoFinanceiro.objects.create(
            tipo="pagar", descricao="Boleto", valor="123",
            categoria=self.categoria, recebedor_nome="Cooperativa Horizonte",
            data_vencimento=date(2026, 9, 10),
        )
        for nome, esperado, total in (("horizonte", livre.pk, "123"), ("Rural", self.lancamento.pk, "500")):
            params = {"recebedor": nome, "tipo": "pagar"}
            resposta = self.client.get(reverse("lancamentos-list"), params)
            self.assertEqual([item["id"] for item in resposta.data], [esperado])
            resumo = self.client.get(reverse("lancamentos-resumo"), params)
            self.assertEqual(Decimal(resumo.data["a_pagar"]), Decimal(total))

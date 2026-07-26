from datetime import date
from decimal import Decimal
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import ClimaCornBelt, CotacaoMercado, NoticiaMercado
from .services import (
    SERIES_MERCADO,
    ServicoMercadoError,
    atualizar_clima_corn_belt,
    atualizar_cotacoes,
    buscar_clima_corn_belt,
    buscar_cotacoes,
    resumir_produto,
)


def csv_fred(url):
    serie = parse_qs(urlparse(url).query)["id"][0]
    return (
        f"observation_date,{serie}\n"
        "2026-05-01,100.00\n"
        "2026-06-01,110.00\n"
    )


def resposta_clima(_url):
    return {
        "daily": {
            "time": ["2026-07-26", "2026-07-27"],
            "temperature_2m_min": [-1, 20],
            "temperature_2m_max": [18, 36],
            "precipitation_sum": [55, 0],
        }
    }


class ServicosMercadoTests(TestCase):
    def test_normaliza_csv_fred(self):
        cotacoes = buscar_cotacoes(CotacaoMercado.Produto.SOJA, transport=csv_fred)

        self.assertEqual(len(cotacoes), 2)
        self.assertEqual(cotacoes[-1]["valor"], Decimal("110.0000"))
        self.assertEqual(cotacoes[-1]["fonte"], "FRED / FMI")

    def test_rejeita_produto_desconhecido(self):
        with self.assertRaisesMessage(ServicoMercadoError, "não reconhecido"):
            buscar_cotacoes("cafe", transport=csv_fred)

    def test_atualizacao_de_cotacoes_e_idempotente(self):
        atualizar_cotacoes(transport=csv_fred)
        atualizar_cotacoes(transport=csv_fred)

        self.assertEqual(CotacaoMercado.objects.count(), len(SERIES_MERCADO) * 2)

    def test_resumo_calcula_variacao_e_aviso(self):
        CotacaoMercado.objects.create(
            produto=CotacaoMercado.Produto.MILHO,
            data=date(2026, 5, 1),
            valor="100",
            unidade="US$/tonelada métrica",
        )
        CotacaoMercado.objects.create(
            produto=CotacaoMercado.Produto.MILHO,
            data=date(2026, 6, 1),
            valor="110",
            unidade="US$/tonelada métrica",
        )

        resumo = resumir_produto(CotacaoMercado.Produto.MILHO)

        self.assertEqual(resumo["variacao_percentual"], Decimal("10.00"))
        self.assertIn("não constitui recomendação", resumo["aviso"])

    def test_normaliza_clima_e_combina_alertas(self):
        previsoes = buscar_clima_corn_belt(
            ClimaCornBelt.Regiao.IOWA,
            transport=resposta_clima,
        )

        self.assertIn("risco de geada", previsoes[0]["alerta"])
        self.assertIn("chuva intensa", previsoes[0]["alerta"])
        self.assertIn("calor com baixa precipitação", previsoes[1]["alerta"])

    def test_atualizacao_do_corn_belt_e_idempotente(self):
        atualizar_clima_corn_belt(transport=resposta_clima)
        atualizar_clima_corn_belt(transport=resposta_clima)

        self.assertEqual(ClimaCornBelt.objects.count(), 10)

    def test_rejeita_series_climaticas_inconsistentes(self):
        def resposta_invalida(_url):
            dados = resposta_clima(_url)
            dados["daily"]["precipitation_sum"] = [0]
            return dados

        with self.assertRaisesMessage(ServicoMercadoError, "Corn Belt"):
            buscar_clima_corn_belt(
                ClimaCornBelt.Regiao.IOWA,
                transport=resposta_invalida,
            )

    def test_impede_cotacao_duplicada(self):
        dados = {
            "produto": CotacaoMercado.Produto.TRIGO,
            "data": date(2026, 6, 1),
            "valor": "200",
            "unidade": "US$/tonelada métrica",
        }
        CotacaoMercado.objects.create(**dados)

        with self.assertRaises(IntegrityError), transaction.atomic():
            CotacaoMercado.objects.create(**dados)


class MercadoApiTests(APITestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(
            username="mercado",
            password="senha-segura",
        )
        self.cotacao = CotacaoMercado.objects.create(
            produto=CotacaoMercado.Produto.SOJA,
            data=date(2026, 6, 1),
            valor="450",
            unidade="US$/tonelada métrica",
        )
        self.previsao = ClimaCornBelt.objects.create(
            regiao=ClimaCornBelt.Regiao.IOWA,
            data=date(2026, 7, 26),
            temperatura_min="18",
            temperatura_max="30",
            precipitacao_mm="4",
        )

    def test_exige_autenticacao(self):
        for nome in ("cotacoes-list", "corn-belt-list", "noticias-list"):
            self.assertEqual(self.client.get(reverse(nome)).status_code, 401)

    def test_filtra_cotacoes_e_corn_belt(self):
        self.client.force_authenticate(self.usuario)

        cotacoes = self.client.get(
            reverse("cotacoes-list"),
            {"produto": CotacaoMercado.Produto.SOJA},
        )
        clima = self.client.get(
            reverse("corn-belt-list"),
            {"regiao": ClimaCornBelt.Regiao.IOWA},
        )

        self.assertEqual(cotacoes.status_code, 200)
        self.assertEqual(len(cotacoes.data), 1)
        self.assertEqual(clima.status_code, 200)
        self.assertEqual(len(clima.data), 1)

    @patch("apps.mercado.views.atualizar_cotacoes")
    def test_acao_atualizar_cotacoes(self, atualizar):
        atualizar.return_value = [self.cotacao]
        self.client.force_authenticate(self.usuario)

        resposta = self.client.post(reverse("cotacoes-atualizar"), {})

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.data["registros_processados"], 1)

    @patch("apps.mercado.views.atualizar_clima_corn_belt")
    def test_acao_atualizar_corn_belt(self, atualizar):
        atualizar.return_value = [self.previsao]
        self.client.force_authenticate(self.usuario)

        resposta = self.client.post(reverse("corn-belt-atualizar"), {})

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.data["registros_processados"], 1)

    @patch("apps.mercado.views.atualizar_cotacoes")
    def test_falha_externa_retorna_503(self, atualizar):
        atualizar.side_effect = ServicoMercadoError("fonte indisponível")
        self.client.force_authenticate(self.usuario)

        resposta = self.client.post(reverse("cotacoes-atualizar"), {})

        self.assertEqual(resposta.status_code, 503)

    def test_crud_de_noticias_e_https(self):
        self.client.force_authenticate(self.usuario)
        dados = {
            "titulo": "Safra norte-americana",
            "resumo": "Atualização informativa.",
            "fonte": "USDA",
            "url": "https://example.com/noticia",
            "publicada_em": timezone.now().isoformat(),
            "ativa": True,
        }

        criada = self.client.post(reverse("noticias-list"), dados)
        invalida = self.client.post(
            reverse("noticias-list"),
            {**dados, "url": "http://example.com/insegura"},
        )

        self.assertEqual(criada.status_code, 201)
        self.assertTrue(NoticiaMercado.objects.filter(pk=criada.data["id"]).exists())
        self.assertEqual(invalida.status_code, 400)

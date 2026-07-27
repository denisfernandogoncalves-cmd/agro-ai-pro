from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.estoque.models import LocalEstoque
from apps.propriedades.models import AcessoPropriedade, Propriedade

from .grain_models import Cultura, Motorista, Safra, Veiculo
from .joint_models import CargaLoteConjunto, LoteConjuntoProducao, ParticipanteLoteConjunto


@override_settings(PROPERTY_ACCESS_LEGACY_TEST_MODE=False)
class RelatoriosTransportesLoteConjuntoTests(APITestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(username="relatorio-conjunto", password="teste")
        self.propriedades = [
            Propriedade.objects.create(nome="Relatório A", municipio="Ivaiporã", uf="PR", area_hectares="20"),
            Propriedade.objects.create(nome="Relatório B", municipio="Arapuã", uf="PR", area_hectares="20"),
        ]
        for propriedade in self.propriedades:
            AcessoPropriedade.objects.create(
                propriedade=propriedade,
                usuario=self.usuario,
                papel=AcessoPropriedade.Papel.ADMINISTRADOR,
            )
        self.cultura = Cultura.objects.create(nome="Trigo conjunto relatório", codigo="trigo-conjunto-relatorio", peso_saca_kg="60")
        self.safra = Safra.objects.create(nome="2027 relatório conjunto")
        self.local = LocalEstoque.objects.create(nome="Armazém relatório conjunto")
        self.motorista = Motorista.objects.create(nome="Motorista Relatório", documento="98765432100")
        self.veiculo = Veiculo.objects.create(placa="BRA2E19", motorista_padrao=self.motorista)
        self.lote = LoteConjuntoProducao.objects.create(
            cultura=self.cultura,
            safra=self.safra,
            data_inicio_colheita="2026-07-20",
            local_armazenagem=self.local,
            criado_por=self.usuario,
        )
        for propriedade in self.propriedades:
            ParticipanteLoteConjunto.objects.create(
                lote=self.lote,
                propriedade=propriedade,
                area_cadastrada_ha="10.0000",
                area_colhida_ha="10.0000",
            )
        CargaLoteConjunto.objects.create(
            lote=self.lote,
            motorista=self.motorista,
            veiculo_cavalo=self.veiculo,
            destino="Cooperativa Central",
            local_armazenagem=self.local,
            peso_bruto_kg="13000.000",
            tara_kg="3000.000",
            peso_liquido_kg="10000.000",
            romaneio="REL-001",
            criado_por=self.usuario,
        )
        CargaLoteConjunto.objects.create(
            lote=self.lote,
            motorista=self.motorista,
            placa_cavalo_informada="BRA-2E19",
            destino="Cooperativa Central",
            local_armazenagem=self.local,
            peso_bruto_kg="11000.000",
            tara_kg="3000.000",
            peso_liquido_kg="8000.000",
            romaneio="REL-002",
            criado_por=self.usuario,
        )
        self.client.force_authenticate(self.usuario)

    def test_exporta_csv_por_motorista_com_quantidade_viagens_e_peso_medio(self):
        resposta = self.client.get(
            "/api/producao/relatorios-transportes-conjuntos/",
            {"agrupamento": "motorista", "formato": "csv"},
        )
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        conteudo = resposta.content.decode("utf-8")
        self.assertIn("Motorista Relatório", conteudo)
        self.assertIn("18000", conteudo)
        self.assertIn("9000", conteudo)
        self.assertIn(",2,", conteudo)

    def test_exporta_por_placa_periodo_lote_e_destino(self):
        for agrupamento in ("placa", "periodo", "lote", "destino"):
            resposta = self.client.get(
                "/api/producao/relatorios-transportes-conjuntos/",
                {"agrupamento": agrupamento, "formato": "csv"},
            )
            self.assertEqual(resposta.status_code, status.HTTP_200_OK, agrupamento)
            self.assertIn("quantidade_kg", resposta.content.decode("utf-8"))

    def test_exporta_xlsx_e_pdf_sem_servico_externo(self):
        resposta_xlsx = self.client.get(
            "/api/producao/relatorios-transportes-conjuntos/",
            {"agrupamento": "motorista", "formato": "xlsx"},
        )
        resposta_pdf = self.client.get(
            "/api/producao/relatorios-transportes-conjuntos/",
            {"agrupamento": "placa", "formato": "pdf"},
        )
        self.assertEqual(resposta_xlsx.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta_pdf.status_code, status.HTTP_200_OK)
        self.assertTrue(resposta_xlsx.content.startswith(b"PK"))
        self.assertTrue(resposta_pdf.content.startswith(b"%PDF"))

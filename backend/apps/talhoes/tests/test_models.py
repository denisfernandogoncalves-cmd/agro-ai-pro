from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.propriedades.models import Propriedade
from apps.talhoes.models import HistoricoAgronomico, Talhao


class TalhaoModelTests(TestCase):
    def setUp(self):
        self.propriedade = Propriedade.objects.create(nome="Fazenda", municipio="Londrina", area_hectares=100)

    def test_exige_area_positiva(self):
        with self.assertRaisesMessage(ValidationError, "maior que zero"):
            Talhao(propriedade=self.propriedade, nome="Norte", area_hectares=0).full_clean()

    def test_exige_propriedade(self):
        with self.assertRaisesMessage(ValidationError, "propriedade é obrigatória"):
            Talhao(nome="Norte", area_hectares=10).full_clean()

    def test_rejeita_soma_superior_a_area_da_propriedade(self):
        Talhao.objects.create(propriedade=self.propriedade, nome="Norte", area_hectares=Decimal("70"))
        with self.assertRaisesMessage(ValidationError, "Disponível: 30.00 ha"):
            Talhao(propriedade=self.propriedade, nome="Sul", area_hectares=Decimal("31")).full_clean()

    def test_aceita_edicao_sem_somar_o_proprio_talhao(self):
        talhao = Talhao.objects.create(propriedade=self.propriedade, nome="Norte", area_hectares=100)
        talhao.nome = "Norte atualizado"
        talhao.full_clean()

    def test_rejeita_produtividade_realizada_negativa(self):
        with self.assertRaisesMessage(ValidationError, "maior ou igual a 0"):
            Talhao(
                propriedade=self.propriedade,
                nome="Norte",
                area_hectares=10,
                produtividade_realizada=Decimal("-1"),
            ).full_clean()

    def test_registra_historico_agronomico(self):
        talhao = Talhao.objects.create(
            propriedade=self.propriedade,
            nome="Norte",
            area_hectares=10,
        )
        historico = HistoricoAgronomico.objects.create(
            talhao=talhao,
            data_referencia="2026-07-25",
            cultura="Soja",
            safra="2025/2026",
            produtividade_realizada=Decimal("61.50"),
        )

        self.assertEqual(talhao.historicos_agronomicos.get(), historico)
        self.assertIn("Norte", str(historico))

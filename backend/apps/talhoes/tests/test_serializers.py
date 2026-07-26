from decimal import Decimal
from tempfile import TemporaryDirectory

from django.test import TestCase

from apps.propriedades.models import Propriedade
from apps.talhoes.serializers import HistoricoAgronomicoSerializer, TalhaoSerializer
from apps.talhoes.models import Talhao
from apps.talhoes.tests.factories import kml_upload


class TalhaoSerializerTests(TestCase):
    def setUp(self):
        self.media = TemporaryDirectory()
        self.settings_override = self.settings(MEDIA_ROOT=self.media.name)
        self.settings_override.enable()
        self.propriedade = Propriedade.objects.create(nome="Fazenda", municipio="Londrina", area_hectares=100)

    def tearDown(self):
        self.settings_override.disable()
        self.media.cleanup()

    def test_processa_kml_ao_criar(self):
        serializer = TalhaoSerializer(data={"nome": "Norte", "area_hectares": "20", "propriedade": self.propriedade.pk, "arquivo_kml": kml_upload()})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        talhao = serializer.save()
        self.assertEqual(talhao.geometria_geojson["type"], "Polygon")
        self.assertIsNotNone(talhao.latitude_centro)

    def test_mensagem_clara_quando_area_excede_propriedade(self):
        serializer = TalhaoSerializer(data={"nome": "Norte", "area_hectares": "101", "propriedade": self.propriedade.pk})
        self.assertFalse(serializer.is_valid())
        self.assertIn("soma das áreas", str(serializer.errors))

    def test_aceita_produtividade_realizada(self):
        serializer = TalhaoSerializer(
            data={
                "nome": "Norte",
                "area_hectares": "20",
                "propriedade": self.propriedade.pk,
                "produtividade_esperada": "65.50",
                "produtividade_realizada": "62.75",
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(
            serializer.save().produtividade_realizada,
            Decimal("62.75"),
        )

    def test_valida_produtividade_do_historico(self):
        talhao = Talhao.objects.create(
            nome="Norte",
            area_hectares=20,
            propriedade=self.propriedade,
        )
        serializer = HistoricoAgronomicoSerializer(
            data={
                "talhao": talhao.pk,
                "data_referencia": "2026-07-25",
                "produtividade_realizada": "-1",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("produtividade_realizada", serializer.errors)

    def test_rejeita_historico_sem_dados_agronomicos(self):
        talhao = Talhao.objects.create(
            nome="Norte",
            area_hectares=20,
            propriedade=self.propriedade,
        )
        serializer = HistoricoAgronomicoSerializer(
            data={
                "talhao": talhao.pk,
                "data_referencia": "2026-07-25",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("ao menos um dado agronômico", str(serializer.errors))

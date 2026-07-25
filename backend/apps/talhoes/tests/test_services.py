from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from apps.talhoes.services import processar_kml
from apps.talhoes.tests.factories import kml_upload


class KmlServiceTests(SimpleTestCase):
    def test_prepara_geojson_e_centroide_para_visualizacao(self):
        resultado = processar_kml(kml_upload())
        self.assertEqual(resultado["geometria_geojson"]["type"], "Polygon")
        self.assertAlmostEqual(resultado["longitude_centro"], -49.333333, places=5)
        self.assertAlmostEqual(resultado["latitude_centro"], -20.333333, places=5)

    def test_rejeita_extensao_invalida(self):
        with self.assertRaisesMessage(ValidationError, "extensão .kml"):
            processar_kml(kml_upload("talhao.xml"))

    def test_rejeita_xml_com_doctype(self):
        arquivo = SimpleUploadedFile("ataque.kml", b"<!DOCTYPE foo><kml />")
        with self.assertRaisesMessage(ValidationError, "não permitidas"):
            processar_kml(arquivo)

    def test_rejeita_coordenada_fora_dos_limites(self):
        with self.assertRaisesMessage(ValidationError, "limites geográficos"):
            processar_kml(kml_upload(coordenadas="-50,-20 181,-20 -49,-21 -50,-20"))

    def test_rejeita_poligono_aberto(self):
        with self.assertRaisesMessage(ValidationError, "polígono fechado"):
            processar_kml(kml_upload(coordenadas="-50,-20 -49,-20 -49,-21 -50,-21"))

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from apps.talhoes.services import comparar_areas, processar_kml
from apps.talhoes.tests.factories import kml_upload


class KmlServiceTests(SimpleTestCase):
    def test_prepara_geojson_e_centroide_para_visualizacao(self):
        resultado = processar_kml(kml_upload())
        self.assertEqual(resultado["geometria_geojson"]["type"], "Polygon")
        self.assertAlmostEqual(resultado["longitude_centro"], -49.333333, places=5)
        self.assertAlmostEqual(resultado["latitude_centro"], -20.333333, places=5)
        self.assertGreater(resultado["area_calculada_hectares"], 0)

    def test_calcula_area_geodesica_conhecida_em_hectares(self):
        resultado = processar_kml(
            kml_upload(coordenadas="0,0 0.01,0 0.01,0.01 0,0.01 0,0")
        )

        self.assertAlmostEqual(
            float(resultado["area_calculada_hectares"]),
            123.6434,
            places=2,
        )

    def test_desconta_anel_interno_e_soma_multiplos_poligonos(self):
        conteudo = b"""<?xml version="1.0"?>
        <kml xmlns="http://www.opengis.net/kml/2.2"><Document>
          <Placemark><Polygon>
            <outerBoundaryIs><LinearRing><coordinates>
              0,0 0.02,0 0.02,0.02 0,0.02 0,0
            </coordinates></LinearRing></outerBoundaryIs>
            <innerBoundaryIs><LinearRing><coordinates>
              0.005,0.005 0.015,0.005 0.015,0.015 0.005,0.015 0.005,0.005
            </coordinates></LinearRing></innerBoundaryIs>
          </Polygon></Placemark>
          <Placemark><Polygon><outerBoundaryIs><LinearRing><coordinates>
            0.03,0 0.04,0 0.04,0.01 0.03,0.01 0.03,0
          </coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark>
        </Document></kml>"""

        resultado = processar_kml(SimpleUploadedFile("multi.kml", conteudo))

        self.assertEqual(resultado["geometria_geojson"]["type"], "MultiPolygon")
        self.assertAlmostEqual(
            float(resultado["area_calculada_hectares"]),
            494.5736,
            places=2,
        )

    def test_compara_area_sem_bloquear_divergencia(self):
        comparacao = comparar_areas("100.00", "110.0000")

        self.assertEqual(comparacao["diferenca_hectares"], 10)
        self.assertEqual(comparacao["divergencia_percentual"], 10)

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

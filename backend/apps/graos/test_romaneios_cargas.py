from io import BytesIO
from openpyxl import load_workbook
from rest_framework.test import APITestCase
from django.urls import reverse
from apps.accounts.models import AcessoUsuario
from .test_cargas_colhidas import CargaColhidaBase
from .cargas_services import registrar_carga_colhida


class RomaneioCargaTests(CargaColhidaBase, APITestCase):
    def setUp(self):
        self.criar_contexto()
        self.client.force_authenticate(self.usuario)
        self.carga=registrar_carga_colhida(usuario=self.usuario, **{**self.dados_carga(), "peso_total_kg":"1500", "tara_kg":"500"})

    def test_pdf_e_excel_duas_vias_com_pesagem_e_produtor(self):
        pdf=self.client.get(reverse("carga-pdf",args=(self.carga.pk,)))
        self.assertEqual(pdf.status_code,200)
        self.assertTrue(pdf.content.startswith(b"%PDF"))
        self.assertIn(".pdf",pdf["Content-Disposition"])
        excel=self.client.get(reverse("carga-excel",args=(self.carga.pk,)))
        self.assertEqual(excel.status_code,200)
        folha=load_workbook(BytesIO(excel.content)).active
        celulas=[c.value for linha in folha for c in linha if c.value is not None]
        self.assertEqual(celulas.count("Peso total"),2)
        self.assertEqual(celulas.count("1.500,000 kg"),2)
        self.assertEqual(celulas.count(f"{self.propriedade.nome} / {self.cad_pro.codigo}"),2)
        self.assertFalse(any(c.data_type=="f" for linha in folha for c in linha))

    def test_download_exige_permissao_imprimir(self):
        AcessoUsuario.objects.create(usuario=self.usuario,modulos=["cargas"],permissoes={"cargas":["consultar"]})
        for rota in ("carga-pdf","carga-excel"):
            self.assertEqual(self.client.get(reverse(rota,args=(self.carga.pk,))).status_code,403)

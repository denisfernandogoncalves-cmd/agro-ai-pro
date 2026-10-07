from decimal import Decimal
from django.test import SimpleTestCase
from .cargas_services import calcular_peso_liquido

class PHCulturaTests(SimpleTestCase):
    def test_ph_so_utilizado_para_trigo(self):
        for cultura in ("Soja","Milho","Trigo"):
            dados={"cultura":cultura,"peso_bruto_kg":"1000","umidade_percentual":"14","impureza_percentual":"0","defeitos_percentual":"0"}
            base=calcular_peso_liquido(**dados)
            com_ph=calcular_peso_liquido(**dados,ph="70",ph_minimo="75",desconto_ph_por_ponto="1")
            self.assertEqual(base[2]-com_ph[2],Decimal("50") if cultura=="Trigo" else Decimal("0"))
            if cultura!="Trigo":
                self.assertIsNone(com_ph[4]["parcelas"]["ph"]["medicao"])

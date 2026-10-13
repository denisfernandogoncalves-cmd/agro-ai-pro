from django.test import SimpleTestCase
from .valores import validar_decimal
from decimal import Decimal
class ValoresTests(SimpleTestCase):
    def test_rejeita_nao_finitos_negativos_e_excesso_de_precisao(self):
        for valor in ["NaN","Infinity","-1","0.001","1000000000000.00","texto"]:
            with self.subTest(valor=valor), self.assertRaises(ValueError):
                validar_decimal(valor,max_digits=14,decimal_places=2)
        self.assertEqual(validar_decimal("0",max_digits=14,decimal_places=2),Decimal("0"))
        self.assertEqual(validar_decimal("123.45",max_digits=14,decimal_places=2),Decimal("123.45"))

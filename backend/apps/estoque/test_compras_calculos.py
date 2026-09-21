from decimal import Decimal

from django.test import SimpleTestCase

from .compras_calculos import calcular_compra


class CalculosCompraTests(SimpleTestCase):
    def test_exemplos_da_planilha(self):
        for qtd, conteudo, custo, total_qtd, valor_base, total in (
            ("143", "5", "370", "715", "74", "52910"),
            ("400", "1000", "2536.80", "400000", "2.5368", "1014720"),
            ("29", "0.1", "0", "2.9", "0", "0"),
        ):
            with self.subTest(qtd=qtd):
                resultado = calcular_compra(qtd, conteudo, custo)
                self.assertEqual(resultado["quantidade"], Decimal(total_qtd))
                self.assertEqual(resultado["custo_unitario"], Decimal(valor_base))
                self.assertEqual(resultado["valor_total"], Decimal(total))

    def test_total_preserva_custo_da_embalagem_sem_recalcular_por_valor_arredondado(self):
        resultado = calcular_compra("7", "3", "10")
        self.assertEqual(resultado["custo_unitario"], Decimal("3.3333"))
        self.assertEqual(resultado["valor_total"], Decimal("70.00"))

    def test_rejeita_valores_invalidos_e_perda_de_precisao(self):
        for valores in (("0", "5", "10"), ("1", "0", "10"), ("1", "5", "-1"),
                        ("0.001", "0.001", "1"), ("NaN", "5", "10"),
                        ("100000000000", "1", "1")):
            with self.subTest(valores=valores), self.assertRaises(ValueError):
                calcular_compra(*valores)

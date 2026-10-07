"""Composição da pesagem, preservando entradas antigas sem tara."""
from decimal import Decimal


def peso_produto(peso_bruto_kg, peso_total_kg=None, tara_kg=None):
    if peso_total_kg is None and tara_kg is None:
        return peso_bruto_kg
    if peso_total_kg is None or tara_kg is None:
        raise ValueError("Informe peso total e tara juntos.")
    total, tara = Decimal(str(peso_total_kg)), Decimal(str(tara_kg))
    if not total.is_finite() or not tara.is_finite() or tara < 0 or total <= tara:
        raise ValueError("O peso total deve ser maior que a tara, que não pode ser negativa.")
    return (total - tara).quantize(Decimal("0.001"))

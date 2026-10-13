from decimal import Decimal
from rest_framework import serializers

def validar_decimal(valor, *, max_digits, decimal_places, minimo=Decimal("0")):
    try:
        return serializers.DecimalField(max_digits=max_digits,decimal_places=decimal_places,min_value=minimo).run_validation(valor)
    except serializers.ValidationError as exc:
        raise ValueError("Informe um número finito, positivo ou zero, com precisão compatível com o campo.") from exc

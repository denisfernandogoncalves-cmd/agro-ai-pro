from apps.maquinas.models import CompraDiesel
from rest_framework import serializers


def ultima_compra_diesel(data, tipo):
    compra = CompraDiesel.objects.filter(data__lte=data, tipo=tipo, excluido_em__isnull=True).order_by("-data", "-id").first()
    if compra is None:
        raise serializers.ValidationError({"tipo_diesel": "Nenhuma compra deste diesel até a data do abastecimento. Cadastre a compra do silo primeiro."})
    return compra

"""Validação sem conversão; conversão apenas quando solicitada pela API."""
import re
from decimal import Decimal, ROUND_HALF_UP
from rest_framework import serializers

PADRAO_GMS = re.compile(r'''^(\d{1,3})(?:[°º]|\s+)\s*(\d{1,2})(?:['′’´]|\s+)\s*(\d{1,2}(?:[.,]\d+)?)["″”'′’´]{0,2}\s*([NSEOW])$''', re.I)


def validar_gms(valor, eixo):
    match = PADRAO_GMS.fullmatch(str(valor).strip())
    if not match:
        raise ValueError('Informe graus, minutos, segundos e hemisfério, como 24°18\'28,97"S.')
    graus, minutos, segundos = [Decimal(v.replace(',', '.')) for v in match.groups()[:3]]
    hemisferio = match.group(4).upper()
    limite = Decimal(90 if eixo=='latitude' else 180)
    permitidos = 'NS' if eixo=='latitude' else 'EOW'
    if hemisferio not in permitidos or not 0 <= minutos < 60 or not 0 <= segundos < 60 or graus > limite or (graus==limite and (minutos or segundos)):
        raise ValueError('Confira os limites dos graus, minutos, segundos e o hemisfério da coordenada.')
    return graus, minutos, segundos, hemisferio


def converter_gms(valor, eixo):
    graus, minutos, segundos, hemisferio = validar_gms(valor,eixo)
    decimal = graus + minutos/60 + segundos/3600
    if hemisferio in 'SOW':
        decimal = -decimal
    return decimal.quantize(Decimal('.000001'), rounding=ROUND_HALF_UP)


def validar_coordenadas_cadastradas(attrs, instance=None):
    converter = attrs.pop('converter_coordenadas', False)
    formato = attrs.get('formato_coordenadas',getattr(instance,'formato_coordenadas','decimal'))
    if converter and formato != 'gms':
        raise serializers.ValidationError({'converter_coordenadas':'Selecione GMS para solicitar a conversão para decimal.'})
    if formato != 'gms':
        return
    lat = attrs.get('latitude_gms',getattr(instance,'latitude_gms','')).strip()
    lon = attrs.get('longitude_gms',getattr(instance,'longitude_gms','')).strip()
    if bool(lat) != bool(lon):
        raise serializers.ValidationError('Informe latitude e longitude em GMS juntas.')
    for eixo,valor in [('latitude',lat),('longitude',lon)]:
        if valor:
            try:
                validar_gms(valor,eixo)
            except ValueError as exc:
                raise serializers.ValidationError({eixo+'_gms':str(exc)}) from exc
    mudou = instance is None or lat != getattr(instance,'latitude_gms','') or lon != getattr(instance,'longitude_gms','') or formato != getattr(instance,'formato_coordenadas','decimal')
    if converter:
        if not lat or not lon:
            raise serializers.ValidationError({'converter_coordenadas':'Informe as duas coordenadas GMS antes de converter.'})
        attrs['latitude'] = converter_gms(lat,'latitude')
        attrs['longitude'] = converter_gms(lon,'longitude')
    elif mudou:
        # GMS novo não deve reutilizar a posição decimal antiga no mapa.
        attrs['latitude'] = None
        attrs['longitude'] = None
    attrs['latitude_gms'] = lat
    attrs['longitude_gms'] = lon

"""Serviços seguros de leitura, validação e medição de geometrias KML."""

from decimal import Decimal, ROUND_HALF_UP
from math import pi, sin
from pathlib import Path
from xml.etree import ElementTree

from django.core.exceptions import ValidationError

MAX_KML_SIZE = 5 * 1024 * 1024
# Raio da esfera autálica do WGS84. A esfera autálica preserva áreas e evita
# escolher uma projeção UTM inadequada para geometrias que cruzem zonas.
RAIO_AUTALICO_WGS84_METROS = 6_371_007.1809


def _ler_upload(arquivo):
    if Path(arquivo.name).suffix.lower() != ".kml":
        raise ValidationError("Envie um arquivo com extensão .kml.")
    if arquivo.size > MAX_KML_SIZE:
        raise ValidationError("O arquivo KML deve ter no máximo 5 MB.")
    posicao = arquivo.tell()
    conteudo = arquivo.read(MAX_KML_SIZE + 1)
    arquivo.seek(posicao)
    if len(conteudo) > MAX_KML_SIZE:
        raise ValidationError("O arquivo KML deve ter no máximo 5 MB.")
    if b"<!DOCTYPE" in conteudo.upper() or b"<!ENTITY" in conteudo.upper():
        raise ValidationError("O arquivo KML contém declarações XML não permitidas.")
    return conteudo


def _coordenadas(texto):
    pontos = []
    for item in (texto or "").split():
        partes = item.split(",")
        if len(partes) < 2:
            raise ValidationError("O polígono KML contém coordenadas inválidas.")
        try:
            longitude, latitude = float(partes[0]), float(partes[1])
        except (TypeError, ValueError):
            raise ValidationError("O polígono KML contém coordenadas inválidas.") from None
        if not -180 <= longitude <= 180 or not -90 <= latitude <= 90:
            raise ValidationError("As coordenadas do KML estão fora dos limites geográficos.")
        pontos.append([longitude, latitude])
    if len(pontos) < 4 or pontos[0] != pontos[-1] or len({tuple(p) for p in pontos[:-1]}) < 3:
        raise ValidationError("O KML deve conter um polígono fechado com ao menos três pontos distintos.")
    return pontos


def _centroide_visual(pontos):
    """Centroide cartesiano para posicionar o mapa; nunca representa área oficial."""
    area_dupla = cx = cy = 0.0
    for atual, seguinte in zip(pontos, pontos[1:]):
        cruzado = atual[0] * seguinte[1] - seguinte[0] * atual[1]
        area_dupla += cruzado
        cx += (atual[0] + seguinte[0]) * cruzado
        cy += (atual[1] + seguinte[1]) * cruzado
    if abs(area_dupla) < 1e-12:
        raise ValidationError("O polígono KML não pode ter área geométrica nula.")
    return {"longitude": cx / (3 * area_dupla), "latitude": cy / (3 * area_dupla)}


def _delta_longitude_radianos(longitude_inicial, longitude_final):
    """Normaliza o arco para lidar com anéis próximos ao antimeridiano."""
    delta = (longitude_final - longitude_inicial) * pi / 180
    if delta > pi:
        return delta - 2 * pi
    if delta < -pi:
        return delta + 2 * pi
    return delta


def _area_anel_metros_quadrados(pontos):
    """Calcula a área geodésica aproximada de um anel na esfera autálica."""
    acumulado = 0.0
    for atual, seguinte in zip(pontos, pontos[1:]):
        latitude_atual = atual[1] * pi / 180
        latitude_seguinte = seguinte[1] * pi / 180
        acumulado += _delta_longitude_radianos(atual[0], seguinte[0]) * (
            2 + sin(latitude_atual) + sin(latitude_seguinte)
        )
    return abs(acumulado) * RAIO_AUTALICO_WGS84_METROS**2 / 2


def _area_poligono_metros_quadrados(aneis):
    area_externa = _area_anel_metros_quadrados(aneis[0])
    area_interna = sum(_area_anel_metros_quadrados(anel) for anel in aneis[1:])
    area = area_externa - area_interna
    if area <= 0:
        raise ValidationError(
            "Os anéis internos do KML não podem ocupar toda a área do polígono."
        )
    return area


def calcular_area_hectares(poligonos):
    """Soma polígonos e desconta seus anéis internos, retornando hectares."""
    metros_quadrados = sum(
        _area_poligono_metros_quadrados(aneis) for aneis in poligonos
    )
    return Decimal(str(metros_quadrados / 10_000)).quantize(
        Decimal("0.0001"),
        rounding=ROUND_HALF_UP,
    )


def comparar_areas(area_declarada, area_calculada):
    """Retorna diferença assinada e percentual sem impor limite de aceitação."""
    if area_declarada is None or area_calculada is None:
        return {"diferenca_hectares": None, "divergencia_percentual": None}
    declarada = Decimal(area_declarada)
    calculada = Decimal(area_calculada)
    diferenca = (calculada - declarada).quantize(
        Decimal("0.0001"),
        rounding=ROUND_HALF_UP,
    )
    percentual = (diferenca / declarada * 100).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )
    return {
        "diferenca_hectares": diferenca,
        "divergencia_percentual": percentual,
    }


def processar_kml(arquivo):
    try:
        raiz = ElementTree.fromstring(_ler_upload(arquivo))
    except ElementTree.ParseError:
        raise ValidationError("Não foi possível ler o XML do arquivo KML.") from None
    elementos_poligono = [elemento for elemento in raiz.iter() if elemento.tag.rsplit("}", 1)[-1] == "Polygon"]
    poligonos = []
    for poligono in elementos_poligono:
        aneis = [elemento for elemento in poligono.iter() if elemento.tag.rsplit("}", 1)[-1] == "coordinates"]
        if aneis:
            poligonos.append([_coordenadas(elemento.text) for elemento in aneis])
    if not poligonos:
        raise ValidationError("O arquivo KML não contém um polígono.")
    # O primeiro perímetro exterior é usado somente para centralizar a visualização.
    centroide = _centroide_visual(poligonos[0][0])
    geometria = (
        {"type": "Polygon", "coordinates": poligonos[0]}
        if len(poligonos) == 1
        else {"type": "MultiPolygon", "coordinates": poligonos}
    )
    return {
        "geometria_geojson": geometria,
        "latitude_centro": centroide["latitude"],
        "longitude_centro": centroide["longitude"],
        "area_calculada_hectares": calcular_area_hectares(poligonos),
    }

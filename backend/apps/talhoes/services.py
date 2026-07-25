"""Serviços seguros de leitura e validação de KML de talhões."""

from pathlib import Path
from xml.etree import ElementTree

from django.core.exceptions import ValidationError

MAX_KML_SIZE = 5 * 1024 * 1024


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
    }

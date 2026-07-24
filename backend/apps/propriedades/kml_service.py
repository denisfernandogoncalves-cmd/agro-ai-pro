from fastkml import kml
from shapely.geometry import shape


def extrair_centroide_kml(arquivo):

    with open(arquivo, "rb") as f:
        conteudo = f.read()

    documento = kml.KML.from_string(conteudo)

    doc = list(documento.features)[0]

    pasta = list(doc.features)[0]

    placemark = list(pasta.features)[0]

    geometria = placemark.kml_geometry

    poligono = geometria.kml_geometries[0].geometry

    centro = shape(poligono).centroid

    return {
        "longitude": centro.x,
        "latitude": centro.y,
    }

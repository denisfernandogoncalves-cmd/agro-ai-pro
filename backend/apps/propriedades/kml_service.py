from fastkml import kml
from shapely.geometry import shape


def extrair_centroide_kml(arquivo):

    with open(arquivo, "rb") as f:
        conteudo = f.read()

    documento = kml.KML()
    documento.from_string(conteudo)

    for doc in documento.features:

        for pasta in doc.features:

            for placemark in pasta.features:

                geometria = placemark.kml_geometry

                if geometria:

                    poligono = geometria.kml_geometries[0].geometry

                    centro = poligono.centroid

                    return {
                        "longitude": centro.x,
                        "latitude": centro.y,
                    }

    return None
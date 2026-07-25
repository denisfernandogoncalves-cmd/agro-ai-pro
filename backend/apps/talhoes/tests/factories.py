from django.core.files.uploadedfile import SimpleUploadedFile


def kml_upload(nome="talhao.kml", coordenadas="-50,-20 -49,-20 -49,-21 -50,-20"):
    conteudo = f"""<?xml version="1.0"?><kml xmlns="http://www.opengis.net/kml/2.2">
    <Document><Placemark><Polygon><outerBoundaryIs><LinearRing>
    <coordinates>{coordenadas}</coordinates>
    </LinearRing></outerBoundaryIs></Polygon></Placemark></Document></kml>"""
    return SimpleUploadedFile(nome, conteudo.encode(), content_type="application/vnd.google-earth.kml+xml")

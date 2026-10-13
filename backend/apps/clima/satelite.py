"""Catálogo público NASA GIBS; não envia coordenadas ou dados operacionais."""
from datetime import date
import urllib.request
import xml.etree.ElementTree as ET
from django.core.cache import cache
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from apps.accounts.access import pode
from rest_framework.response import Response
from rest_framework.views import APIView

GIBS = "https://gibs.earthdata.nasa.gov/wms/epsg3857/best/wms.cgi"
CAMADAS = {
    "MODIS_Terra_CorrectedReflectance_TrueColor": ("Satélite MODIS — cor natural", "250 m", "Diária"),
    "MODIS_Terra_L3_NDVI_16Day": ("NDVI MODIS — composição regional", "250 m", "16 dias"),
}


def extrair_camadas(xml):
    resultado = []
    for camada in ET.fromstring(xml).iter("Layer"):
        nome = camada.findtext("Name")
        if nome not in CAMADAS:
            continue
        tempo = next((e for e in camada.findall("Extent") if e.get("name") == "time"), None)
        if tempo is None:
            continue
        data = tempo.get("default", "")
        date.fromisoformat(data)
        titulo, resolucao, periodo = CAMADAS[nome]
        resultado.append({"camada": nome, "titulo": titulo, "data": data,
                          "resolucao": resolucao, "periodo": periodo})
    if len(resultado) != len(CAMADAS):
        raise ValueError("Camadas esperadas ausentes no catálogo NASA.")
    return resultado


class SateliteView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not pode(request.user, "clima", "consultar"):
            raise PermissionDenied("Seu usuário não pode consultar o clima.")
        dados = cache.get("gibs-camadas-v1")
        if dados is None:
            try:
                with urllib.request.urlopen(GIBS + "?SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.1.1", timeout=15) as resposta:
                    xml = resposta.read(8_000_001)
                if len(xml) > 8_000_000:
                    raise ValueError("Catálogo excede limite.")
                dados = extrair_camadas(xml)
                cache.set("gibs-camadas-v1", dados, 21600)
            except (OSError, ValueError, ET.ParseError):
                return Response({"detail": "NASA GIBS indisponível. Tente novamente mais tarde."}, status=503)
        return Response({"fonte": "NASA GIBS / MODIS", "url": GIBS, "camadas": dados})

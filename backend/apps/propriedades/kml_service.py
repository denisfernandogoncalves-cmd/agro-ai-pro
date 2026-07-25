"""Compatibilidade do processamento KML de propriedades sem dependências opcionais."""

from django.core.files import File

from apps.talhoes.services import processar_kml


def extrair_centroide_kml(caminho):
    with open(caminho, "rb") as arquivo_aberto:
        resultado = processar_kml(File(arquivo_aberto, name=caminho))
    return {
        "longitude": resultado["longitude_centro"],
        "latitude": resultado["latitude_centro"],
    }

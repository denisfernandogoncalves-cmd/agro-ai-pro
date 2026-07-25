"""Compatibilidade do processamento KML de propriedades."""

from pathlib import Path

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files import File

from apps.talhoes.services import processar_kml


class KMLInvalidoError(ValueError):
    """Erro de domínio para uploads KML inválidos em Propriedades."""


def _processar(arquivo):
    try:
        resultado = processar_kml(arquivo)
    except DjangoValidationError as exc:
        raise KMLInvalidoError(" ".join(exc.messages)) from exc
    return {
        "longitude": resultado["longitude_centro"],
        "latitude": resultado["latitude_centro"],
    }


def extrair_centroide_kml(arquivo):
    if hasattr(arquivo, "read"):
        return _processar(arquivo)

    caminho = Path(arquivo)
    with caminho.open("rb") as arquivo_aberto:
        return _processar(File(arquivo_aberto, name=caminho.name))

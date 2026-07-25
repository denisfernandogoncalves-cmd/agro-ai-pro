from .kml_service import extrair_centroide_kml


def atualizar_coordenadas_kml(propriedade):
    if not propriedade.arquivo_kml:
        return None

    resultado = extrair_centroide_kml(propriedade.arquivo_kml)
    propriedade.latitude = resultado["latitude"]
    propriedade.longitude = resultado["longitude"]
    propriedade.save(update_fields=["latitude", "longitude"])

    return resultado

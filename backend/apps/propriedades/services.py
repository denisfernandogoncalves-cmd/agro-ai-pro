from .kml_service import extrair_centroide_kml


def atualizar_coordenadas_kml(propriedade):
    if not propriedade.arquivo_kml:
        return None

    resultado = extrair_centroide_kml(propriedade.arquivo_kml)
    propriedade.latitude = resultado["latitude"]
    propriedade.longitude = resultado["longitude"]
    propriedade.geometria_geojson = resultado["geometria_geojson"]
    propriedade.area_calculada_hectares = resultado["area_calculada_hectares"]
    propriedade.save(
        update_fields=[
            "latitude",
            "longitude",
            "geometria_geojson",
            "area_calculada_hectares",
        ]
    )

    return resultado

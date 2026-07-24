import requests


def buscar_previsao(latitude, longitude):

    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={latitude}"
        f"&longitude={longitude}"
        "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum"
        "&timezone=America/Sao_Paulo"
    )

    resposta = requests.get(url)

    if resposta.status_code != 200:
        return None

    dados = resposta.json()

    return {
        "data": dados["daily"]["time"][0],
        "temperatura_max": dados["daily"]["temperature_2m_max"][0],
        "temperatura_min": dados["daily"]["temperature_2m_min"][0],
        "chuva_mm": dados["daily"]["precipitation_sum"][0],
    }
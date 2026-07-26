"""Integra√ß√£o resiliente com o provedor gratuito Open-Meteo."""

from datetime import date
from decimal import Decimal
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from django.db import transaction

from .models import PrevisaoClima


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT_SEGUNDOS = 10
VARIAVEIS_DIARIAS = (
    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "precipitation_probability_max",
    "wind_speed_10m_max",
    "relative_humidity_2m_mean",
)

CONDICOES_WMO = {
    0: "C√©u limpo",
    1: "Predominantemente limpo",
    2: "Parcialmente nublado",
    3: "Nublado",
    45: "Neblina",
    48: "Neblina com geada",
    51: "Garoa fraca",
    53: "Garoa moderada",
    55: "Garoa forte",
    61: "Chuva fraca",
    63: "Chuva moderada",
    65: "Chuva forte",
    80: "Pancadas de chuva fracas",
    81: "Pancadas de chuva moderadas",
    82: "Pancadas de chuva fortes",
    95: "Trovoadas",
    96: "Trovoadas com granizo",
    99: "Trovoadas fortes com granizo",
}


class ServicoClimaError(RuntimeError):
    """Falha tratada de comunica√ß√£o ou contrato com o provedor clim√°tico."""


def _decimal(valor):
    return None if valor is None else Decimal(str(valor)).quantize(Decimal("0.01"))


def _inteiro(valor):
    return None if valor is None else round(float(valor))


def gerar_alerta_agricola(previsao):
    alertas = []
    if previsao["temperatura_min"] is not None and previsao["temperatura_min"] <= 3:
        alertas.append("Risco de geada")
    if previsao["temperatura_max"] is not None and previsao["temperatura_max"] >= 35:
        alertas.append("Calor intenso")
    if previsao["chuva_mm"] is not None and previsao["chuva_mm"] >= 50:
        alertas.append("Chuva intensa")
    if previsao["vento_kmh"] is not None and previsao["vento_kmh"] >= 40:
        alertas.append("Vento forte")
    if previsao["umidade"] is not None and previsao["umidade"] <= 30:
        alertas.append("Umidade baixa")
    return "; ".join(alertas)


def _normalizar_resposta(dados):
    diario = dados.get("daily")
    if not isinstance(diario, dict) or not diario.get("time"):
        raise ServicoClimaError("O provedor retornou uma previs√£o incompleta.")

    quantidade = len(diario["time"])
    campos = {
        "temperatura_max": diario.get("temperature_2m_max", []),
        "temperatura_min": diario.get("temperature_2m_min", []),
        "chuva_mm": diario.get("precipitation_sum", []),
        "probabilidade_chuva": diario.get("precipitation_probability_max", []),
        "vento_kmh": diario.get("wind_speed_10m_max", []),
        "umidade": diario.get("relative_humidity_2m_mean", []),
        "codigo_tempo": diario.get("weather_code", []),
    }
    if any(len(valores) != quantidade for valores in campos.values()):
        raise ServicoClimaError("O provedor retornou s√©ries clim√°ticas inconsistentes.")

    previsoes = []
    for indice, data_iso in enumerate(diario["time"]):
        codigo = _inteiro(campos["codigo_tempo"][indice])
        previsao = {
            "data": date.fromisoformat(data_iso),
            "temperatura_max": _decimal(campos["temperatura_max"][indice]),
            "temperatura_min": _decimal(campos["temperatura_min"][indice]),
            "chuva_mm": _decimal(campos["chuva_mm"][indice]),
            "probabilidade_chuva": _inteiro(
                campos["probabilidade_chuva"][indice]
            ),
            "vento_kmh": _decimal(campos["vento_kmh"][indice]),
            "umidade": _inteiro(campos["umidade"][indice]),
            "codigo_tempo": codigo,
            "condicao": CONDICOES_WMO.get(codigo, "Condi√ß√£o vari√°vel"),
            "fonte": "Open-Meteo",
        }
        previsao["alerta_agricola"] = gerar_alerta_agricola(previsao)
        previsoes.append(previsao)
    return previsoes


def _consultar_open_meteo(parametros):
    url = f"{OPEN_METEO_URL}?{urlencode(parametros)}"
    with urlopen(url, timeout=TIMEOUT_SEGUNDOS) as resposta:
        return json.loads(resposta.read().decode("utf-8"))


def buscar_previsoes(latitude, longitude, transport=_consultar_open_meteo):
    parametros = {
        "latitude": float(latitude),
        "longitude": float(longitude),
        "daily": ",".join(VARIAVEIS_DIARIAS),
        "timezone": "America/Sao_Paulo",
        "forecast_days": 7,
    }
    try:
        dadou”^ˆ∂âûÀk∫wµÁO^ 
HOàŸ][Ÿ[ ù[Ÿ\»ä_BàÇà[0ÌY\¬àÿù]€èÇàù]€Çà€\‹”ò[YO^€[Ÿ[»OOHò€[XHà»àààúŸX›[ô\ö[»üBà€ê€X⁄œ^ 
HOàŸ][Ÿ[ ò€[XHä_BàÇà€[XBàÿù]€èÇà€ò]èÇÇà€[Ÿ[»OOHù[Ÿ\»à»
à[Ÿ\‘YŸHœÇà
Hà[Ÿ[»OOHò€[XHà»
à€[XTYŸHõ‹öYYY\œ^‹õ‹öYYY\ﬂHœÇà
Hà
àÇàŸ\úõ»	âà€\‹”ò[YOHô\úõ»ÿ\ôèûŸ\úõﬂO‹üBÇàŸX›[€à€\‹”ò[YOHô‹òYHèÇàõ‹õH€\‹”ò[YOHòÿ\ôõ‹õ][\ö[»à€î›XõZ]^‹ÿ[ò\üOÇàèûŸYXÿ[“Y»ëY]\àõ‹öYYYHààìõ›òHõ‹öYYYHüO⁄èÇàXô[ìõ€YO[ú]ô\]Z\ôYò[YO^Ÿõ‹õ][\ö[Àõõ€Y_H€ê⁄[ôŸO^ JHOàŸ]õ‹õ][\ö[ »ããôõ‹õ][\ö[Àõ€YNàKù\ôŸ]ùò[YHJ_Hœè€Xô[ÇàXô[îõ‹öY]0Ë\ö[œ[ú]ò[YO^Ÿõ‹õ][\ö[Àúõ‹öY]\ö[ﬂH€ê⁄[ôŸO^ JHOàŸ]õ‹õ][\ö[ »ããôõ‹õ][\ö[Àõ‹öY]\ö[ŒàKù\ôŸ]ùò[YHJ_Hœè€Xô[Çà]à€\‹”ò[YOHõ[öHèÇàXô[ì][öXÎ\[œ[ú]ô\]Z\ôYò[YO^Ÿõ‹õ][\ö[Àõ][öX⁄\[ﬂH€ê⁄[ôŸO^ JHOàŸ]õ‹õ][\ö[ »ããôõ‹õ][\ö[À][öX⁄\[ŒàKù\ôŸ]ùò[YHJ_Hœè€Xô[ÇàXô[ïQè[ú]X^[ô›^ÃüHò[YO^Ÿõ‹õ][\ö[ÀùYüH€ê⁄[ôŸO^ JHOàŸ]õ‹õ][\ö[ »ããôõ‹õ][\ö[ÀYéàKù\ôŸ]ùò[YKù’\\êÿ\ŸJ
HJ_Hœè€Xô[ÇàŸ]èÇàXô[∞‡\ôXH
JO[ú]ô\]Z\ôYZ[èHååHà›\HååHà\OHõù[Xô\ààò[YO^Ÿõ‹õ][\ö[Àò\ôXW⁄X›\ô\ﬂH€ê⁄[ôŸO^ JHOàŸ]õ‹õ][\ö[ »ããôõ‹õ][\ö[À\ôXW⁄X›\ô\ŒàKù\ôŸ]ùò[YHJ_Hœè€Xô[Çà]à€\‹”ò[YOHõ[öHèÇàXô[ì]]YO[ú]›\Hò[ûHà\OHõù[Xô\ààò[YO^Ÿõ‹õ][\ö[Àõ]]Y_H€ê⁄[ôŸO^ JHOàŸ]õ‹õ][\ö[ »ããôõ‹õ][\ö[À]]YNàKù\ôŸ]ùò[YHJ_Hœè€Xô[ÇàXô[ì€ô⁄]YO[ú]›\Hò[ûHà\OHõù[Xô\ààò[YO^Ÿõ‹õ][\ö[Àõ€ô⁄]Y_H€ê⁄[ôŸO^ JHOàŸ]õ‹õ][\ö[ »ããôõ‹õ][\ö[À€ô⁄]YNàKù\ôŸ]ùò[YHJ_Hœè€Xô[ÇàŸ]èÇàXô[í”S
]0ÍHHPäO[ú]XÿŸ\Hãö€[à\OHôö[Hà€ê⁄[ôŸO^ JHOàŸ]õ‹õ][\ö[ »ããôõ‹õ][\ö[À\ú]Z]õ◊⁄€[àKù\ôŸ]ôö[\œÀñÃHœ»ù[J_Hœè€Xô[ÇàXô[ìÿúŸ\ùòpÈÌY\œ^\ôXHò[YO^Ÿõ‹õ][\ö[ÀõÿúŸ\ùòX€Ÿ\ﬂH€ê⁄[ôŸO^ JHOàŸ]õ‹õ][\ö[ »ããôõ‹õ][\ö[ÀÿúŸ\ùòX€Ÿ\ŒàKù\ôŸ]ùò[YHJ_Hœè€Xô[Çà]à€\‹”ò[YOHòX€Ÿ\»èÇàù]€à\ÿXõY^ÿÿ\úôYÿ[ôﬂH\OHú›XõZ]èîÿ[ò\èÿù]€èÇàŸYXÿ[“Y	âàù]€à€\‹”ò[YOHúŸX›[ô\ö[»à\OHòù]€àà€ê€X⁄œ^ 
HOà»Ÿ]YXÿ[“Y
ù[
N»Ÿ]õ‹õ][\ö[ õ‹õ][\ö[’ò^ö[ N»_Oêÿ[òŸ[\èÿù]€èüBàŸ]èÇàŸõ‹õOÇÇàŸX›[€à€\‹”ò[YOHò€€ù]Y»èÇàõ‹õH€\‹”ò[YOHòù\ÿÿHà€î›XõZ]^ JHOà»Kúô]ô[ùYò][

N»õ⁄Yÿ\úôYÿ\äù\ÿÿJN»_OÇà[ú]\öXK[Xô[Hêù\ÿÿ\àõ‹öYYY\»àXŸZ€\èHêù\ÿÿ\à‹àõ€YK][öXÎ\[»›Hõ‹öY]0Ë\ö[»àò[YO^ÿù\ÿÿ_H€ê⁄[ôŸO^ JHOàŸ]ù\ÿÿJKù\ôŸ]ùò[YJ_HœÇàù]€à\OHú›XõZ]èêù\ÿÿ\èÿù]€èÇàŸõ‹õOÇÇàÿÿ\úôYÿ[ô»	âàõ‹öYYY\Àõ[ô›OOH»
àêÿ\úôYÿ[ô»õ‹öYYY\Àããè‹Çà
Hàõ‹öYYY\Àõ[ô›OOH»
à]à€\‹”ò[YOHòÿ\ôò^ö[»èìô[ö[XHõ‹öYYYHÿY\›òYKèŸ]èÇà
Hà
à]à€\‹”ò[YOHõ\›HèÇà‹õ‹öYYY\ÀõX\

][JHOà
à\ùX€H€\‹”ò[YO^ÿÿ\ô][H	‹Ÿ[X⁄[€òYOÀöYOOH][KöY»ò]]õ»àààüXHŸ^O^⁄][KöYH€ê€X⁄œ^ 
HOàŸ]Ÿ[X⁄[€òYJ][J_OÇà]èÇàœû⁄][Kõõ€Y_O⁄œÇàû⁄][Kõ][öX⁄\[ﬂKﬁ⁄][KùYüH0≠»⁄][Kò\ôXW⁄X›\ô\ﬂHHX€\òY‹œ‹Çà⁄][Kò\ôXWÿÿ[›[YW⁄X›\ô\»	âà
à€\‹”ò[YOHõY]YYÀYŸ[Ÿ‹òYöX€»èÇà⁄][Kò\ôXWÿÿ[›[YW⁄X›\ô\ﬂHHÿ[›[Y‹¬à⁄][Kô]ô\ôŸ[ò⁄XWÿ\ôXW‹\òŸ[ùX[	âÇà0≠»Yô\ô[∞ÈÿH	⁄][Kô]ô\ôŸ[ò⁄XWÿ\ôXW‹\òŸ[ùX[IXBà‹Çà
_BàŸ]èÇà]à€\‹”ò[YOHòX€Ÿ\»èÇàù]€à€\‹”ò[YOHúŸX›[ô\ö[»à€ê€X⁄œ^ JHOà»Kú›‹õ‹Yÿ][€ä
N»Y]\ä][JN»_OëY]\èÿù]€èÇàù]€à€\‹”ò[YOHú\öY€»à€ê€X⁄œ^ JHOà»Kú›‹õ‹Yÿ][€ä
N»õ⁄Y^€Z\ä][JN»_Oë^€Z\èÿù]€èÇàŸ]èÇàÿ\ùX€OÇà
J_BàŸ]èÇà
_BÇà‹Ÿ[X⁄[€òYOÀõ]]YH	âàŸ[X⁄[€òYKõ€ô⁄]YH	âà
àX\Tõ‹öYYYBà]]YO^”ù[Xô\äŸ[X⁄[€òYKõ]]YJ_Bà€ô⁄]YO^”ù[Xô\äŸ[X⁄[€òYKõ€ô⁄]YJ_Bàõ€YO^‹Ÿ[X⁄[€òYKõõ€Y_BàŸ[€Y]öXO^‹Ÿ[X⁄[€òYKôŸ[€Y]öXWŸŸ[⁄ú€€üBàœÇà
_Bà‹ŸX›[€èÇà‹ŸX›[€èÇàœÇà
_Bà€XZ[èÇà
N¬üB
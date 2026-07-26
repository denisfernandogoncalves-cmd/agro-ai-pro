"""Previsão automática, cacheada e resiliente para propriedades autorizadas."""

from datetime import date, datetime, timedelta
from decimal import Decimal
import hashlib
import json
from types import SimpleNamespace
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from apps.propriedades.models import Propriedade

from .models import (
    AlertaClimatico,
    AtualizacaoClima,
    ConfiguracaoClima,
    PrevisaoClima,
    PrevisaoHoraria,
)


OPEN_METEO_URL = getattr(
    settings,
    "CLIMA_PROVIDER_BASE_URL",
    "https://api.open-meteo.com/v1/forecast",
)
TIMEOUT_SEGUNDOS = int(getattr(settings, "CLIMA_PROVIDER_TIMEOUT_SECONDS", 15))
CACHE_SEGUNDOS = int(getattr(settings, "CLIMA_PROVIDER_CACHE_SECONDS", 900))
LOCK_SEGUNDOS = int(getattr(settings, "CLIMA_UPDATE_LOCK_SECONDS", 180))
MAX_ATUALIZACOES_CICLO = int(getattr(settings, "CLIMA_MAX_UPDATES_PER_CYCLE", 100))

VARIAVEIS_DIARIAS = (
    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "apparent_temperature_max",
    "apparent_temperature_min",
    "precipitation_sum",
    "precipitation_probability_max",
    "wind_speed_10m_max",
    "wind_gusts_10m_max",
    "wind_direction_10m_dominant",
    "relative_humidity_2m_mean",
    "pressure_msl_mean",
    "cloud_cover_mean",
    "shortwave_radiation_sum",
    "dew_point_2m_mean",
    "et0_fao_evapotranspiration",
    "sunrise",
    "sunset",
)
VARIAVEIS_HORARIAS = (
    "temperature_2m",
    "relative_humidity_2m",
    "dew_point_2m",
    "apparent_temperature",
    "precipitation_probability",
    "precipitation",
    "weather_code",
    "cloud_cover",
    "pressure_msl",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
    "shortwave_radiation",
    "et0_fao_evapotranspiration",
)
VARIAVEIS_ATUAIS = (
    "temperature_2m",
    "relative_humidity_2m",
    "apparent_temperature",
    "precipitation",
    "weather_code",
    "cloud_cover",
    "pressure_msl",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
)

CONDICOES_WMO = {
    0: "Céu limpo",
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
    66: "Chuva congelante fraca",
    67: "Chuva congelante forte",
    71: "Neve fraca",
    73: "Neve moderada",
    75: "Neve forte",
    80: "Pancadas de chuva fracas",
    81: "Pancadas de chuva moderadas",
    82: "Pancadas de chuva fortes",
    85: "Pancadas de neve fracas",
    86: "Pancadas de neve fortes",
    95: "Trovoadas",
    96: "Trovoadas com granizo",
    99: "Trovoadas fortes com granizo",
}


class ServicoClimaError(RuntimeError):
    """Falha tratada de localização, comunicação ou contrato climático."""


class AtualizacaoClimaEmAndamento(ServicoClimaError):
    """Evita duas atualizações simultâneas da mesma propriedade."""


def _decimal(valor, casas="0.01"):
    return None if valor is None else Decimal(str(valor)).quantize(Decimal(casas))


def _inteiro(valor):
    return None if valor is None else round(float(valor))


def _data_hora(valor):
    if not valor:
        return None
    resultado = datetime.fromisoformat(str(valor))
    if timezone.is_naive(resultado):
        resultado = timezone.make_aware(resultado, timezone.get_current_timezone())
    return resultado


def _valor(serie, indice, padrao=None):
    if not isinstance(serie, list) or indice >= len(serie):
        return padrao
    return serie[indice]


def _limites_padrao():
    return SimpleNamespace(
        limite_geada_c=Decimal("3"),
        limite_calor_c=Decimal("35"),
        limite_frio_c=Decimal("8"),
        limite_chuva_forte_mm=Decimal("50"),
        limite_vento_forte_kmh=Decimal("40"),
        limite_umidade_alta=90,
        limite_umidade_baixa=30,
        limite_deriva_vento_kmh=Decimal("15"),
        limite_lavagem_chuva_mm=Decimal("5"),
        dias_sem_chuva_alerta=7,
    )


def avaliar_condicoes_agronomicas(dados, configuracao=None):
    configuracao = configuracao or _limites_padrao()
    vento = _decimal(dados.get("vento_kmh"))
    chuva = _decimal(dados.get("chuva_mm") or dados.get("precipitacao_mm"))
    probabilidade = _inteiro(dados.get("probabilidade_chuva"))
    umidade = _inteiro(dados.get("umidade"))
    temperatura = _decimal(
        dados.get("temperatura")
        or dados.get("temperatura_max")
        or dados.get("temperatura_min")
    )
    risco_deriva = bool(
        vento is not None
        and vento >= Decimal(str(configuracao.limite_deriva_vento_kmh))
    )
    risco_lavagem = bool(
        (chuva is not None and chuva >= Decimal(str(configuracao.limite_lavagem_chuva_mm)))
        or (probabilidade is not None and probabilidade >= 60)
    )
    pulverizacao = "favoravel"
    if risco_deriva or risco_lavagem:
        pulverizacao = "desfavoravel"
    elif (
        temperatura is None
        or umidade is None
        or not 10 <= temperatura <= 30
        or not 45 <= umidade <= 85
    ):
        pulverizacao = "atencao"
    colheita = "favoravel"
    if risco_lavagem or (umidade is not None and umidade >= 90):
        colheita = "desfavoravel"
    elif chuva is None or probabilidade is None:
        colheita = "atencao"
    return {
        "condicao_pulverizacao": pulverizacao,
        "condicao_colheita": colheita,
        "risco_deriva": risco_deriva,
        "risco_lavagem": risco_lavagem,
    }


def gerar_alerta_agricola(previsao, configuracao=None):
    configuracao = configuracao or _limites_padrao()
    alertas = []
    temperatura_min = _decimal(previsao.get("temperatura_min"))
    temperatura_max = _decimal(previsao.get("temperatura_max"))
    chuva = _decimal(previsao.get("chuva_mm"))
    vento = _decimal(previsao.get("vento_kmh"))
    umidade = _inteiro(previsao.get("umidade"))
    codigo = _inteiro(previsao.get("codigo_tempo"))
    if temperatura_min is not None and temperatura_min <= Decimal(str(configuracao.limite_geada_c)):
        alertas.append("Risco de geada")
    if temperatura_min is not None and temperatura_min <= Decimal(str(configuracao.limite_frio_c)):
        alertas.append("Temperatura baixa")
    if temperatura_max is not None and temperatura_max >= Decimal(str(configuracao.limite_calor_c)):
        alertas.append("Calor intenso")
    if chuva is not None and chuva >= Decimal(str(configuracao.limite_chuva_forte_mm)):
        alertas.append("Chuva intensa")
    if vento is not None and vento >= Decimal(str(configuracao.limite_vento_forte_kmh)):
        alertas.append("Vento forte")
    if umidade is not None and umidade <= configuracao.limite_umidade_baixa:
        alertas.append("Umidade baixa")
    if umidade is not None and umidade >= configuracao.limite_umidade_alta:
        alertas.append("Excesso de umidade")
    if codigo in {95, 96, 99}:
        alertas.append("Risco de tempestade")
    if codigo in {96, 99}:
        alertas.append("Possibilidade de granizo")
    return "; ".join(dict.fromkeys(alertas))


def _normalizar_diario(dados, configuracao=None):
    diario = dados.get("daily")
    if not isinstance(diario, dict) or not diario.get("time"):
        raise ServicoClimaError("O provedor retornou uma previsão diária incompleta.")
    previsoes = []
    for indice, data_iso in enumerate(diario["time"]):
        codigo = _inteiro(_valor(diario.get("weather_code"), indice))
        previsao = {
            "data": date.fromisoformat(data_iso),
            "temperatura_max": _decimal(_valor(diario.get("temperature_2m_max"), indice)),
            "temperatura_min": _decimal(_valor(diario.get("temperature_2m_min"), indice)),
            "sensacao_max": _decimal(_valor(diario.get("apparent_temperature_max"), indice)),
            "sensacao_min": _decimal(_valor(diario.get("apparent_temperature_min"), indice)),
            "chuva_mm": _decimal(_valor(diario.get("precipitation_sum"), indice)),
            "probabilidade_chuva": _inteiro(_valor(diario.get("precipitation_probability_max"), indice)),
            "vento_kmh": _decimal(_valor(diario.get("wind_speed_10m_max"), indice)),
            "rajada_vento_kmh": _decimal(_valor(diario.get("wind_gusts_10m_max"), indice)),
            "direcao_vento": _inteiro(_valor(diario.get("wind_direction_10m_dominant"), indice)),
            "umidade": _inteiro(_valor(diario.get("relative_humidity_2m_mean"), indice)),
            "pressao_hpa": _decimal(_valor(diario.get("pressure_msl_mean"), indice)),
            "cobertura_nuvens": _inteiro(_valor(diario.get("cloud_cover_mean"), indice)),
            "radiacao_solar_mj": _decimal(_valor(diario.get("shortwave_radiation_sum"), indice)),
            "ponto_orvalho": _decimal(_valor(diario.get("dew_point_2m_mean"), indice)),
            "evapotranspiracao_mm": _decimal(_valor(diario.get("et0_fao_evapotranspiration"), indice)),
            "nascer_sol": _data_hora(_valor(diario.get("sunrise"), indice)),
            "por_sol": _data_hora(_valor(diario.get("sunset"), indice)),
            "codigo_tempo": codigo,
            "condicao": CONDICOES_WMO.get(codigo, "Condição variável"),
            "fonte": "Open-Meteo",
        }
        previsao.update(avaliar_condicoes_agronomicas(previsao, configuracao))
        previsao["risco_estresse_hidrico"] = bool(
            (previsao["chuva_mm"] or 0) == 0
            and previsao["temperatura_max"] is not None
            and previsao["temperatura_max"] >= 30
        )
        previsao["alerta_agricola"] = gerar_alerta_agricola(previsao, configuracao)
        previsoes.append(previsao)
    return previsoes


def _normalizar_horario(dados, configuracao=None):
    horario = dados.get("hourly")
    if not isinstance(horario, dict) or not horario.get("time"):
        return []
    previsoes = []
    for indice, data_iso in enumerate(horario["time"]):
        codigo = _inteiro(_valor(horario.get("weather_code"), indice))
        previsao = {
            "data_hora": _data_hora(data_iso),
            "temperatura": _decimal(_valor(horario.get("temperature_2m"), indice)),
            "sensacao_termica": _decimal(_valor(horario.get("apparent_temperature"), indice)),
            "umidade": _inteiro(_valor(horario.get("relative_humidity_2m"), indice)),
            "precipitacao_mm": _decimal(_valor(horario.get("precipitation"), indice)),
            "probabilidade_chuva": _inteiro(_valor(horario.get("precipitation_probability"), indice)),
            "vento_kmh": _decimal(_valor(horario.get("wind_speed_10m"), indice)),
            "direcao_vento": _inteiro(_valor(horario.get("wind_direction_10m"), indice)),
            "rajada_vento_kmh": _decimal(_valor(horario.get("wind_gusts_10m"), indice)),
            "pressao_hpa": _decimal(_valor(horario.get("pressure_msl"), indice)),
            "cobertura_nuvens": _inteiro(_valor(horario.get("cloud_cover"), indice)),
            "radiacao_solar": _decimal(_valor(horario.get("shortwave_radiation"), indice)),
            "ponto_orvalho": _decimal(_valor(horario.get("dew_point_2m"), indice)),
            "evapotranspiracao_mm": _decimal(_valor(horario.get("et0_fao_evapotranspiration"), indice), "0.001"),
            "codigo_tempo": codigo,
            "condicao": CONDICOES_WMO.get(codigo, "Condição variável"),
            "fonte": "Open-Meteo",
        }
        previsao.update(avaliar_condicoes_agronomicas(previsao, configuracao))
        previsoes.append(previsao)
    return previsoes


def _normalizar_atual(dados):
    atual = dados.get("current")
    if not isinstance(atual, dict):
        return {}
    codigo = _inteiro(atual.get("weather_code"))
    campos = {
        "data_hora": atual.get("time"),
        "temperatura": atual.get("temperature_2m"),
        "sensacao_termica": atual.get("apparent_temperature"),
        "umidade": atual.get("relative_humidity_2m"),
        "precipitacao_mm": atual.get("precipitation"),
        "cobertura_nuvens": atual.get("cloud_cover"),
        "pressao_hpa": atual.get("pressure_msl"),
        "vento_kmh": atual.get("wind_speed_10m"),
        "direcao_vento": atual.get("wind_direction_10m"),
        "rajada_vento_kmh": atual.get("wind_gusts_10m"),
        "codigo_tempo": codigo,
        "condicao": CONDICOES_WMO.get(codigo, "Condição variável"),
        "fonte": "Open-Meteo",
    }
    return {chave: valor for chave, valor in campos.items() if valor is not None}


def _consultar_open_meteo(parametros):
    url = f"{OPEN_METEO_URL}?{urlencode(parametros)}"
    with urlopen(url, timeout=TIMEOUT_SEGUNDOS) as resposta:
        return json.loads(resposta.read().decode("utf-8"))


def _chave_cache(parametros):
    serializado = json.dumps(parametros, sort_keys=True, separators=(",", ":"))
    return "clima:provider:" + hashlib.sha256(serializado.encode("utf-8")).hexdigest()


def _consultar_cacheado(parametros, transport, force=False):
    if transport is not _consultar_open_meteo:
        return transport(parametros), False
    chave = _chave_cache(parametros)
    if not force:
        armazenado = cache.get(chave)
        if armazenado is not None:
            return armazenado, True
    dados = transport(parametros)
    cache.set(chave, dados, timeout=CACHE_SEGUNDOS)
    return dados, False


def buscar_previsoes(latitude, longitude, transport=_consultar_open_meteo):
    parametros = {
        "latitude": float(latitude),
        "longitude": float(longitude),
        "daily": ",".join(VARIAVEIS_DIARIAS),
        "timezone": "America/Sao_Paulo",
        "forecast_days": 7,
    }
    try:
        dados = transport(parametros)
    except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
        raise ServicoClimaError("Não foi possível consultar o serviço meteorológico.") from exc
    return _normalizar_diario(dados)


def buscar_pacote_climatico(latitude, longitude, altitude=None, transport=_consultar_open_meteo, force=False):
    parametros = {
        "latitude": float(latitude),
        "longitude": float(longitude),
        "current": ",".join(VARIAVEIS_ATUAIS),
        "hourly": ",".join(VARIAVEIS_HORARIAS),
        "daily": ",".join(VARIAVEIS_DIARIAS),
        "timezone": "America/Sao_Paulo",
        "forecast_days": 7,
        "past_days": 1,
        "cell_selection": "land",
    }
    if altitude is not None:
        parametros["elevation"] = float(altitude)
    try:
        dados, veio_cache = _consultar_cacheado(parametros, transport, force=force)
    except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
        raise ServicoClimaError("Não foi possível consultar o serviço meteorológico.") from exc
    return {
        "diarias": _normalizar_diario(dados),
        "horarias": _normalizar_horario(dados),
        "atual": _normalizar_atual(dados),
        "cache": veio_cache,
    }


def _pontos_geojson(geometria):
    pontos = []

    def percorrer(valor):
        if isinstance(valor, (list, tuple)):
            if len(valor) >= 2 and all(isinstance(item, (int, float)) for item in valor[:2]):
                pontos.append((float(valor[1]), float(valor[0])))
            else:
                for item in valor:
                    percorrer(item)

    if isinstance(geometria, dict):
        percorrer(geometria.get("coordinates", []))
    return pontos


def _centroide_geojson(geometria):
    pontos = _pontos_geojson(geometria)
    if not pontos:
        return None
    latitudes = [ponto[0] for ponto in pontos]
    longitudes = [ponto[1] for ponto in pontos]
    return ((min(latitudes) + max(latitudes)) / 2, (min(longitudes) + max(longitudes)) / 2)


def obter_coordenadas_propriedade(propriedade):
    if propriedade.latitude is not None and propriedade.longitude is not None:
        return float(propriedade.latitude), float(propriedade.longitude), "cadastro", _altitude_propriedade(propriedade)
    centroide = _centroide_geojson(propriedade.geometria_geojson)
    if centroide:
        return centroide[0], centroide[1], "geojson_propriedade", _altitude_propriedade(propriedade)
    gerenciador = getattr(propriedade, "talhoes", None)
    if gerenciador is not None:
        for talhao in gerenciador.all().order_by("id"):
            if talhao.latitude_centro is not None and talhao.longitude_centro is not None:
                return float(talhao.latitude_centro), float(talhao.longitude_centro), "centro_talhao", talhao.altitude_media
            centroide = _centroide_geojson(talhao.geometria_geojson)
            if centroide:
                return centroide[0], centroide[1], "geojson_talhao", talhao.altitude_media
    return None


def _altitude_propriedade(propriedade):
    gerenciador = getattr(propriedade, "talhoes", None)
    if gerenciador is None:
        return None
    valores = list(
        gerenciador.exclude(altitude_media__isnull=True).values_list("altitude_media", flat=True)
    )
    if not valores:
        return None
    return sum(Decimal(str(valor)) for valor in valores) / len(valores)


def _nivel_alerta(texto):
    if any(termo in texto for termo in ("geada", "Chuva intensa", "tempestade", "granizo")):
        return AlertaClimatico.Nivel.CRITICO
    return AlertaClimatico.Nivel.ATENCAO


def _sincronizar_alertas(propriedade, configuracao, diarias, horarias):
    agora = timezone.now()
    chaves_ativas = set()
    for previsao in diarias:
        if not previsao["alerta_agricola"]:
            continue
        chave = f"diario:{previsao['data'].isoformat()}:{hashlib.sha1(previsao['alerta_agricola'].encode()).hexdigest()[:12]}"
        chaves_ativas.add(chave)
        AlertaClimatico.objects.update_or_create(
            propriedade=propriedade,
            chave=chave,
            defaults={
                "tipo": "previsao_diaria",
                "nivel": _nivel_alerta(previsao["alerta_agricola"]),
                "titulo": "Alerta climático automático",
                "descricao": previsao["alerta_agricola"],
                "inicio": timezone.make_aware(datetime.combine(previsao["data"], datetime.min.time())),
                "fim": timezone.make_aware(datetime.combine(previsao["data"], datetime.max.time())),
                "ativo": True,
            },
        )
    proximas_24h = [item for item in horarias if item["data_hora"] and agora <= item["data_hora"] <= agora + timedelta(hours=24)]
    for tipo, campo, titulo in (
        ("risco_deriva", "risco_deriva", "Risco de deriva nas próximas 24 horas"),
        ("risco_lavagem", "risco_lavagem", "Risco de lavagem por chuva nas próximas 24 horas"),
    ):
        janela = [item for item in proximas_24h if item[campo]]
        if janela:
            chave = f"{tipo}:{agora.date().isoformat()}"
            chaves_ativas.add(chave)
            AlertaClimatico.objects.update_or_create(
                propriedade=propriedade,
                chave=chave,
                defaults={
                    "tipo": tipo,
                    "nivel": AlertaClimatico.Nivel.ATENCAO,
                    "titulo": titulo,
                    "descricao": "Revise a previsão horária antes de programar aplicações.",
                    "inicio": janela[0]["data_hora"],
                    "fim": janela[-1]["data_hora"],
                    "ativo": True,
                },
            )
    dias_analisados = diarias[: configuracao.dias_sem_chuva_alerta]
    if len(dias_analisados) == configuracao.dias_sem_chuva_alerta and sum(item["chuva_mm"] or 0 for item in dias_analisados) < Decimal("1"):
        chave = f"sem_chuva:{agora.date().isoformat()}:{configuracao.dias_sem_chuva_alerta}"
        chaves_ativas.add(chave)
        AlertaClimatico.objects.update_or_create(
            propriedade=propriedade,
            chave=chave,
            defaults={
                "tipo": "ausencia_chuva",
                "nivel": AlertaClimatico.Nivel.ATENCAO,
                "titulo": "Ausência prolongada de chuva",
                "descricao": f"Não há chuva relevante prevista para os próximos {configuracao.dias_sem_chuva_alerta} dias.",
                "inicio": agora,
                "fim": agora + timedelta(days=configuracao.dias_sem_chuva_alerta),
                "ativo": True,
            },
        )
    AlertaClimatico.objects.filter(propriedade=propriedade, ativo=True).exclude(chave__in=chaves_ativas).update(ativo=False)


def _registro_ignorado(propriedade, mensagem):
    return AtualizacaoClima.objects.create(
        propriedade=propriedade,
        finalizada_em=timezone.now(),
        status=AtualizacaoClima.Status.IGNORADA,
        mensagem=mensagem,
    )


def atualizar_clima_propriedade(propriedade, transport=_consultar_open_meteo, force=False):
    configuracao, _ = ConfiguracaoClima.objects.get_or_create(propriedade=propriedade)
    agora = timezone.now()
    if not configuracao.ativo:
        _registro_ignorado(propriedade, "Atualização automática desativada.")
        return {"previsoes": list(propriedade.previsoes_clima.all()), "cache": False, "ignorada": True}
    if not force and configuracao.proxima_atualizacao and configuracao.proxima_atualizacao > agora:
        _registro_ignorado(propriedade, "Previsão ainda está dentro da janela de atualização.")
        return {"previsoes": list(propriedade.previsoes_clima.all()), "cache": True, "ignorada": True}
    chave_lock = f"clima:update-lock:{propriedade.pk}"
    if not cache.add(chave_lock, "1", timeout=LOCK_SEGUNDOS):
        raise AtualizacaoClimaEmAndamento("Já existe uma atualização climática em andamento para esta propriedade.")
    registro = AtualizacaoClima.objects.create(
        propriedade=propriedade,
        status=AtualizacaoClima.Status.IGNORADA,
    )
    try:
        coordenadas = obter_coordenadas_propriedade(propriedade)
        if not coordenadas:
            configuracao.status = ConfiguracaoClima.Status.SEM_LOCALIZACAO
            configuracao.ultima_tentativa = agora
            configuracao.erro_ultima_atualizacao = "Complete as coordenadas ou a geometria da propriedade."
            configuracao.proxima_atualizacao = agora + timedelta(minutes=configuracao.frequencia_minutos)
            configuracao.save()
            registro.status = AtualizacaoClima.Status.ERRO
            registro.tipo_erro = "sem_localizacao"
            registro.mensagem = configuracao.erro_ultima_atualizacao
            registro.finalizada_em = timezone.now()
            registro.save()
            raise ServicoClimaError(configuracao.erro_ultima_atualizacao)
        latitude, longitude, origem, altitude = coordenadas
        configuracao.status = ConfiguracaoClima.Status.ATUALIZANDO
        configuracao.ultima_tentativa = agora
        configuracao.origem_coordenadas = origem
        configuracao.latitude_usada = _decimal(latitude, "0.000001")
        configuracao.longitude_usada = _decimal(longitude, "0.000001")
        configuracao.altitude_usada = _decimal(altitude) if altitude is not None else None
        configuracao.save()
        pacote = buscar_pacote_climatico(
            latitude,
            longitude,
            altitude=altitude,
            transport=transport,
            force=force,
        )
        with transaction.atomic():
            resultados = []
            for item in pacote["diarias"]:
                valores = dict(item)
                data_previsao = valores.pop("data")
                previsao, _ = PrevisaoClima.objects.update_or_create(
                    propriedade=propriedade,
                    data=data_previsao,
                    defaults=valores,
                )
                resultados.append(previsao)
            for item in pacote["horarias"]:
                valores = dict(item)
                data_hora = valores.pop("data_hora")
                PrevisaoHoraria.objects.update_or_create(
                    propriedade=propriedade,
                    data_hora=data_hora,
                    defaults=valores,
                )
            PrevisaoHoraria.objects.filter(
                propriedade=propriedade,
                data_hora__lt=agora - timedelta(days=7),
            ).delete()
            _sincronizar_alertas(
                propriedade,
                configuracao,
                pacote["diarias"],
                pacote["horarias"],
            )
            configuracao.status = ConfiguracaoClima.Status.ATUALIZADO
            configuracao.ultima_atualizacao = agora
            configuracao.proxima_atualizacao = agora + timedelta(minutes=configuracao.frequencia_minutos)
            configuracao.erro_ultima_atualizacao = ""
            configuracao.falhas_consecutivas = 0
            configuracao.total_chamadas += 0 if pacote["cache"] else 1
            configuracao.dados_atuais = pacote["atual"]
            configuracao.save()
            registro.status = AtualizacaoClima.Status.CACHE if pacote["cache"] else AtualizacaoClima.Status.SUCESSO
            registro.origem_coordenadas = origem
            registro.chamadas_provedor = 0 if pacote["cache"] else 1
            registro.previsoes_diarias = len(pacote["diarias"])
            registro.previsoes_horarias = len(pacote["horarias"])
            registro.finalizada_em = timezone.now()
            registro.save()
        return {"previsoes": resultados, "cache": pacote["cache"], "ignorada": False}
    except AtualizacaoClimaEmAndamento:
        raise
    except ServicoClimaError as exc:
        if configuracao.status != ConfiguracaoClima.Status.SEM_LOCALIZACAO:
            configuracao.status = ConfiguracaoClima.Status.ERRO
            configuracao.falhas_consecutivas += 1
            espera = min(
                configuracao.frequencia_minutos,
                15 * (2 ** min(configuracao.falhas_consecutivas - 1, 4)),
            )
            configuracao.proxima_atualizacao = agora + timedelta(minutes=espera)
            configuracao.erro_ultima_atualizacao = str(exc)[:240]
            configuracao.save()
            registro.status = AtualizacaoClima.Status.ERRO
            registro.tipo_erro = exc.__class__.__name__
            registro.mensagem = str(exc)[:240]
            registro.finalizada_em = timezone.now()
            registro.save()
        raise
    finally:
        cache.delete(chave_lock)


def atualizar_previsoes(propriedade, transport=_consultar_open_meteo):
    """Mantém o contrato existente da atualização manual."""
    return atualizar_clima_propriedade(
        propriedade,
        transport=transport,
        force=True,
    )["previsoes"]


def atualizar_clima_pendente(limite=None):
    limite = limite or MAX_ATUALIZACOES_CICLO
    resumo = {"atualizadas": 0, "ignoradas": 0, "erros": 0}
    agora = timezone.now()
    for propriedade in Propriedade.objects.all().order_by("id").iterator():
        if sum(resumo.values()) >= limite:
            break
        configuracao, _ = ConfiguracaoClima.objects.get_or_create(propriedade=propriedade)
        if not configuracao.ativo:
            resumo["ignoradas"] += 1
            continue
        if configuracao.proxima_atualizacao and configuracao.proxima_atualizacao > agora:
            resumo["ignoradas"] += 1
            continue
        try:
            resultado = atualizar_clima_propriedade(propriedade, force=False)
            resumo["ignoradas" if resultado["ignorada"] else "atualizadas"] += 1
        except (ServicoClimaError, AtualizacaoClimaEmAndamento):
            resumo["erros"] += 1
    return resumo

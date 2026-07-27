from datetime import timedelta
import hashlib

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .enterprise_models import (
    AtivoMercado,
    AtualizacaoMercado,
    ConfiguracaoAtivoMercado,
    CotacaoAtivoMercado,
)
from .enterprise_providers import (
    ATIVOS,
    ProvedorMercadoError,
    buscar_ptax,
    buscar_stooq,
    obter_json,
    obter_texto,
)


CACHE_SEGUNDOS = 600
LOCK_SEGUNDOS = 300


class ServicoMercadoEnterpriseError(RuntimeError):
    pass


def inicializar_configuracoes():
    configuracoes = []
    frequencia = int(getattr(settings, "MERCADO_UPDATE_FREQUENCY_MINUTES", 15))
    for ativo, dados in ATIVOS.items():
        configuracao, _ = ConfiguracaoAtivoMercado.objects.get_or_create(
            ativo=ativo,
            defaults={
                "provedor": dados["provedor"],
                "simbolo": dados["simbolo"],
                "frequencia_minutos": frequencia,
            },
        )
        configuracoes.append(configuracao)
    return configuracoes


def _cache_key(configuracao):
    bruto = f"{configuracao.ativo}:{configuracao.provedor}:{configuracao.simbolo}"
    return "mercado:provider:" + hashlib.sha256(bruto.encode()).hexdigest()


def _lock_key(configuracao):
    return f"mercado:update-lock:{configuracao.ativo}"


def _sanitizar_erro(exc):
    mensagem = str(exc).replace("http://", "").replace("https://", "")
    return mensagem[:240]


def _buscar(configuracao, *, force=False, text_transport=obter_texto, json_transport=obter_json):
    chave = _cache_key(configuracao)
    if not force:
        cached = cache.get(chave)
        if cached:
            return cached, True, 0
    if configuracao.provedor == "bcb_ptax":
        dados = buscar_ptax(transport=json_transport)
    else:
        dados = buscar_stooq(configuracao.ativo, transport=text_transport)
    cache.set(
        chave,
        dados,
        int(getattr(settings, "MERCADO_PROVIDER_CACHE_SECONDS", CACHE_SEGUNDOS)),
    )
    return dados, False, 2 if configuracao.provedor == "stooq" else 1


def _salvar_ponto(configuracao, intervalo, dados):
    defaults = {
        "abertura": dados.get("abertura"),
        "maxima": dados.get("maxima"),
        "minima": dados.get("minima"),
        "fechamento": dados["fechamento"],
        "volume": dados.get("volume"),
        "unidade": ATIVOS[configuracao.ativo]["unidade"],
        "moeda": ATIVOS[configuracao.ativo]["moeda"],
        "fonte": "Banco Central do Brasil" if configuracao.provedor == "bcb_ptax" else "Stooq",
        "simbolo_origem": configuracao.simbolo,
    }
    return CotacaoAtivoMercado.objects.update_or_create(
        ativo=configuracao.ativo,
        intervalo=intervalo,
        data_hora=dados["data_hora"],
        defaults=defaults,
    )[0]


def atualizar_ativo(
    ativo,
    *,
    force=False,
    text_transport=obter_texto,
    json_transport=obter_json,
):
    inicializar_configuracoes()
    configuracao = ConfiguracaoAtivoMercado.objects.get(ativo=ativo)
    agora = timezone.now()
    if not configuracao.habilitado:
        configuracao.status = ConfiguracaoAtivoMercado.Status.DESATIVADO
        configuracao.save(update_fields=("status", "atualizado_em"))
        return {"ignorada": True, "motivo": "desativado"}
    if not force and configuracao.proxima_atualizacao and configuracao.proxima_atualizacao > agora:
        AtualizacaoMercado.objects.create(
            ativo=ativo,
            status=AtualizacaoMercado.Status.IGNORADA,
            iniciada_em=agora,
            finalizada_em=agora,
            provedor=configuracao.provedor,
        )
        return {"ignorada": True, "motivo": "dentro_da_frequencia"}
    if not cache.add(
        _lock_key(configuracao),
        "1",
        timeout=int(getattr(settings, "MERCADO_UPDATE_LOCK_SECONDS", LOCK_SEGUNDOS)),
    ):
        return {"ignorada": True, "motivo": "atualizacao_em_andamento"}
    inicio = timezone.now()
    configuracao.ultima_tentativa = inicio
    configuracao.save(update_fields=("ultima_tentativa", "atualizado_em"))
    try:
        (snapshot, diarios), cache_hit, chamadas = _buscar(
            configuracao,
            force=force,
            text_transport=text_transport,
            json_transport=json_transport,
        )
        with transaction.atomic():
            configuracao = ConfiguracaoAtivoMercado.objects.select_for_update().get(ativo=ativo)
            ponto_snapshot = _salvar_ponto(
                configuracao,
                CotacaoAtivoMercado.Intervalo.SNAPSHOT,
                snapshot,
            )
            for diario in diarios:
                _salvar_ponto(
                    configuracao,
                    CotacaoAtivoMercado.Intervalo.DIARIO,
                    diario,
                )
            fim = timezone.now()
            configuracao.ultima_atualizacao = fim
            configuracao.proxima_atualizacao = fim + timedelta(minutes=configuracao.frequencia_minutos)
            configuracao.status = ConfiguracaoAtivoMercado.Status.ATUALIZADO
            configuracao.mensagem_erro = ""
            configuracao.falhas_consecutivas = 0
            configuracao.total_chamadas += chamadas
            configuracao.total_atualizacoes += 1
            configuracao.save()
            AtualizacaoMercado.objects.create(
                ativo=ativo,
                status=AtualizacaoMercado.Status.CACHE if cache_hit else AtualizacaoMercado.Status.SUCESSO,
                iniciada_em=inicio,
                finalizada_em=fim,
                provedor=configuracao.provedor,
                chamadas_realizadas=chamadas,
                pontos_snapshot=1,
                pontos_diarios=len(diarios),
                utilizou_cache=cache_hit,
            )
        return {
            "ignorada": False,
            "ativo": ativo,
            "cotacao": ponto_snapshot,
            "diarios": len(diarios),
            "cache": cache_hit,
        }
    except (ProvedorMercadoError, ValueError, TypeError, KeyError) as exc:
        fim = timezone.now()
        with transaction.atomic():
            configuracao = ConfiguracaoAtivoMercado.objects.select_for_update().get(ativo=ativo)
            configuracao.falhas_consecutivas += 1
            espera = min(
                configuracao.frequencia_minutos,
                5 * (2 ** min(configuracao.falhas_consecutivas - 1, 5)),
            )
            configuracao.proxima_atualizacao = fim + timedelta(minutes=espera)
            configuracao.status = ConfiguracaoAtivoMercado.Status.ERRO
            configuracao.mensagem_erro = _sanitizar_erro(exc)
            configuracao.save()
            AtualizacaoMercado.objects.create(
                ativo=ativo,
                status=AtualizacaoMercado.Status.ERRO,
                iniciada_em=inicio,
                finalizada_em=fim,
                provedor=configuracao.provedor,
                tipo_erro=type(exc).__name__,
                mensagem_erro=_sanitizar_erro(exc),
            )
        raise ServicoMercadoEnterpriseError(
            f"Não foi possível atualizar {configuracao.get_ativo_display()}. A última cotação válida foi preservada."
        ) from exc
    finally:
        cache.delete(_lock_key(configuracao))


def atualizar_mercado_pendente(*, limite=None):
    inicializar_configuracoes()
    agora = timezone.now()
    queryset = ConfiguracaoAtivoMercado.objects.filter(
        Q(proxima_atualizacao__isnull=True) | Q(proxima_atualizacao__lte=agora),
        habilitado=True,
    ).order_by("proxima_atualizacao", "ativo")
    if limite:
        queryset = queryset[:limite]
    resultado = {"atualizadas": 0, "ignoradas": 0, "erros": 0}
    for configuracao in queryset:
        try:
            item = atualizar_ativo(configuracao.ativo)
            resultado["ignoradas" if item.get("ignorada") else "atualizadas"] += 1
        except ServicoMercadoEnterpriseError:
            resultado["erros"] += 1
    return resultado


def atualizar_todos(*, force=True):
    inicializar_configuracoes()
    resultados = []
    erros = []
    for ativo, _ in AtivoMercado.choices:
        try:
            resultados.append(atualizar_ativo(ativo, force=force))
        except ServicoMercadoEnterpriseError as exc:
            erros.append({"ativo": ativo, "detail": str(exc)})
    return {"resultados": resultados, "erros": erros}

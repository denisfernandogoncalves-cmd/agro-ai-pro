from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Avg, Max, Min, Sum
from django.utils import timezone

from .enterprise_models import AtivoMercado, ConfiguracaoAtivoMercado, CotacaoAtivoMercado
from .models import ClimaCornBelt


JANELAS = {
    "intraday": (CotacaoAtivoMercado.Intervalo.SNAPSHOT, timedelta(days=1)),
    "5d": (CotacaoAtivoMercado.Intervalo.DIARIO, timedelta(days=8)),
    "30d": (CotacaoAtivoMercado.Intervalo.DIARIO, timedelta(days=45)),
}


def _percentual(atual, anterior):
    if atual is None or not anterior:
        return None
    return ((atual - anterior) / anterior * Decimal("100")).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


def serie_ativo(ativo, janela="30d"):
    intervalo, periodo = JANELAS.get(janela, JANELAS["30d"])
    inicio = timezone.now() - periodo
    queryset = CotacaoAtivoMercado.objects.filter(
        ativo=ativo,
        intervalo=intervalo,
        data_hora__gte=inicio,
    ).order_by("data_hora")
    limite = 300 if janela == "intraday" else 31
    return list(queryset[:limite])


def resumo_ativo(ativo):
    configuracao = ConfiguracaoAtivoMercado.objects.filter(ativo=ativo).first()
    atual = CotacaoAtivoMercado.objects.filter(
        ativo=ativo,
        intervalo=CotacaoAtivoMercado.Intervalo.SNAPSHOT,
    ).order_by("-data_hora").first()
    diarios = list(
        CotacaoAtivoMercado.objects.filter(
            ativo=ativo,
            intervalo=CotacaoAtivoMercado.Intervalo.DIARIO,
        ).order_by("-data_hora")[:2]
    )
    if not atual and diarios:
        atual = diarios[0]
    if not atual:
        return {
            "ativo": ativo,
            "ativo_nome": dict(AtivoMercado.choices).get(ativo, ativo),
            "disponivel": False,
            "status": configuracao.status if configuracao else "pendente",
            "mensagem": configuracao.mensagem_erro if configuracao else "Sem dados persistidos.",
        }
    anterior = diarios[1].fechamento if len(diarios) > 1 else None
    referencia_dia = diarios[0] if diarios else atual
    desatualizado = not configuracao or not configuracao.ultima_atualizacao or (
        timezone.now() - configuracao.ultima_atualizacao
        > timedelta(minutes=max(configuracao.frequencia_minutos * 2, 30))
    )
    return {
        "ativo": ativo,
        "ativo_nome": atual.get_ativo_display(),
        "disponivel": True,
        "cotacao_atual": atual.fechamento,
        "abertura": referencia_dia.abertura,
        "maxima": referencia_dia.maxima,
        "minima": referencia_dia.minima,
        "variacao_diaria": _percentual(referencia_dia.fechamento, anterior),
        "data_hora": atual.data_hora,
        "unidade": atual.unidade,
        "moeda": atual.moeda,
        "fonte": atual.fonte,
        "status": configuracao.status if configuracao else "pendente",
        "ultima_atualizacao": configuracao.ultima_atualizacao if configuracao else None,
        "proxima_atualizacao": configuracao.proxima_atualizacao if configuracao else None,
        "desatualizado": desatualizado,
    }


def _tendencia(ativo):
    pontos = serie_ativo(ativo, "5d")
    if len(pontos) < 2:
        return "neutra", None
    variacao = _percentual(pontos[-1].fechamento, pontos[0].fechamento)
    if variacao is None:
        return "neutra", None
    if variacao >= Decimal("1"):
        return "alta", variacao
    if variacao <= Decimal("-1"):
        return "baixa", variacao
    return "lateral", variacao


def _contexto_corn_belt():
    hoje = timezone.localdate()
    dados = ClimaCornBelt.objects.filter(data__gte=hoje).aggregate(
        chuva_media=Avg("precipitacao_mm"),
        minima=Min("temperatura_min"),
        maxima=Max("temperatura_max"),
    )
    alertas = list(
        ClimaCornBelt.objects.filter(data__gte=hoje)
        .exclude(alerta="")
        .values_list("alerta", flat=True)[:10]
    )
    return {
        "chuva_media": dados["chuva_media"],
        "temperatura_minima": dados["minima"],
        "temperatura_maxima": dados["maxima"],
        "alertas": alertas,
    }


def _contexto_producao(usuario, propriedade=None):
    try:
        from apps.producao.grain_access import filtrar_queryset_por_cadpro
        from apps.producao.grain_models import ContratoProducao, EmbarqueProducao, SaldoGraos
        from apps.producao.joint_services import lotes_conjuntos_visiveis
    except ImportError:
        return {"estoque_kg": Decimal("0"), "contratado_aberto_kg": Decimal("0"), "saldo_conjunto_kg": Decimal("0")}
    saldos = filtrar_queryset_por_cadpro(SaldoGraos.objects.all(), usuario)
    contratos = filtrar_queryset_por_cadpro(
        ContratoProducao.objects.filter(status=ContratoProducao.Status.ABERTO),
        usuario,
    )
    if propriedade:
        saldos = saldos.filter(propriedade_id=propriedade)
        contratos = contratos.filter(propriedade_id=propriedade)
    estoque = saldos.aggregate(total=Sum("quantidade_kg"))["total"] or Decimal("0")
    contratado = Decimal("0")
    for contrato in contratos.prefetch_related("embarques"):
        embarcado = sum(
            (
                item.quantidade_kg
                for item in contrato.embarques.all()
                if item.status == EmbarqueProducao.Status.CONFIRMADO
            ),
            start=Decimal("0"),
        )
        contratado += max(contrato.quantidade_kg - embarcado, Decimal("0"))
    lotes = lotes_conjuntos_visiveis(usuario)
    if propriedade:
        lotes = lotes.filter(participantes__propriedade_id=propriedade)
    saldo_conjunto = sum(
        (
            saldo.quantidade_kg
            for lote in lotes.prefetch_related("saldos_conjuntos")
            for saldo in lote.saldos_conjuntos.all()
        ),
        start=Decimal("0"),
    )
    return {
        "estoque_kg": estoque,
        "contratado_aberto_kg": contratado,
        "saldo_conjunto_kg": saldo_conjunto,
    }


def analise_automatica(usuario=None, propriedade=None):
    resumos = {ativo: resumo_ativo(ativo) for ativo, _ in AtivoMercado.choices}
    corn_belt = _contexto_corn_belt()
    producao = _contexto_producao(usuario, propriedade) if usuario else {}
    fatores_alta = []
    fatores_baixa = []
    impactos = []

    alertas_texto = " ".join(corn_belt["alertas"]).lower()
    chuva = corn_belt["chuva_media"]
    if "baixa precipitação" in alertas_texto or (chuva is not None and chuva < 5):
        fatores_alta.append("Baixa precipitação ou calor seco no Corn Belt pode elevar o prêmio de risco dos grãos.")
        impactos.append({"fator": "Corn Belt", "direcao": "alta", "descricao": "Risco hídrico detectado nas regiões monitoradas."})
    elif chuva is not None and chuva > 35:
        fatores_baixa.append("Chuva ampla no Corn Belt pode favorecer o potencial produtivo e limitar altas.")
        impactos.append({"fator": "Corn Belt", "direcao": "baixa", "descricao": "Precipitação média elevada no horizonte monitorado."})

    for ativo in (AtivoMercado.SOJA_CBOT, AtivoMercado.MILHO_CBOT, AtivoMercado.TRIGO_CBOT):
        tendencia, variacao = _tendencia(ativo)
        nome = dict(AtivoMercado.choices)[ativo]
        if tendencia == "alta":
            fatores_alta.append(f"{nome} apresenta alta de curto prazo de {variacao}%.")
        elif tendencia == "baixa":
            fatores_baixa.append(f"{nome} apresenta baixa de curto prazo de {variacao}%.")

    brent = resumos.get(AtivoMercado.BRENT, {})
    dolar = resumos.get(AtivoMercado.DOLAR, {})
    if brent.get("variacao_diaria") is not None:
        direcao = "alta" if brent["variacao_diaria"] > 0 else "baixa"
        impactos.append({"fator": "Brent", "direcao": direcao, "descricao": f"Variação diária de {brent['variacao_diaria']}%."})
    if dolar.get("variacao_diaria") is not None:
        direcao = "alta" if dolar["variacao_diaria"] > 0 else "baixa"
        impactos.append({"fator": "Dólar", "direcao": direcao, "descricao": f"Variação diária de {dolar['variacao_diaria']}%."})
        if direcao == "alta":
            fatores_alta.append("Dólar mais firme tende a sustentar referências em reais.")
        else:
            fatores_baixa.append("Dólar mais fraco pode reduzir o suporte às referências em reais.")

    estoque_livre = None
    if producao:
        estoque_livre = producao["estoque_kg"] + producao["saldo_conjunto_kg"] - producao["contratado_aberto_kg"]
    saldo_sinais = len(fatores_alta) - len(fatores_baixa)
    if estoque_livre is not None and estoque_livre <= 0:
        recomendacao = "Não há saldo livre suficiente no filtro atual; priorize o cumprimento dos contratos e a conciliação do estoque."
    elif saldo_sinais >= 2:
        recomendacao = "Cenário com mais fatores de sustentação: avaliar venda parcelada de uma fração do saldo livre, mantendo exposição para novas oportunidades."
    elif saldo_sinais <= -2:
        recomendacao = "Cenário pressionado: evitar concentração de decisão em um único preço e revisar necessidade de caixa, contratos e proteção antes de vender."
    else:
        recomendacao = "Cenário misto: trabalhar com alvos e vendas parceladas, condicionadas ao estoque livre, contratos e necessidade de caixa."

    return {
        "gerado_em": timezone.now(),
        "impactos": impactos,
        "fatores_alta": fatores_alta,
        "fatores_baixa": fatores_baixa,
        "tendencia_curto_prazo": "alta" if saldo_sinais > 0 else "baixa" if saldo_sinais < 0 else "mista",
        "recomendacao_operacional": recomendacao,
        "contexto_producao": producao,
        "corn_belt": corn_belt,
        "aviso": "Análise automática de apoio gerencial. Não constitui garantia de preço, recomendação financeira ou ordem de venda.",
    }


def painel_mercado(usuario=None, propriedade=None):
    return {
        "ativos": [resumo_ativo(ativo) for ativo, _ in AtivoMercado.choices],
        "analise": analise_automatica(usuario, propriedade),
        "atualizacoes": list(
            ConfiguracaoAtivoMercado.objects.values(
                "ativo",
                "status",
                "ultima_atualizacao",
                "proxima_atualizacao",
                "mensagem_erro",
                "total_chamadas",
            )
        ),
    }

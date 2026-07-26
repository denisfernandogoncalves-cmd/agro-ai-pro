from decimal import Decimal

from django.db.models import Sum

from apps.mercado.models import CotacaoMercado
from apps.producao.models import (
    ConfiguracaoCultura,
    EmbarqueProducao,
)


PRODUCT_CODES = {
    "soja": CotacaoMercado.Produto.SOJA,
    "milho": CotacaoMercado.Produto.MILHO,
    "trigo": CotacaoMercado.Produto.TRIGO,
}


def adicionar_insights_producao(*, adicionar, recebimentos, saldos_graos, contratos):
    estoque_graos = saldos_graos.aggregate(total=Sum("quantidade_kg"))["total"] or Decimal("0")
    if estoque_graos > 0:
        adicionar(
            "producao_estoque_disponivel",
            "informativo",
            "Estoque de grãos disponível",
            f"O saldo consolidado autorizado é de {estoque_graos:.3f} kg.",
            "Comparar o estoque físico com contratos e estratégia comercial antes de novos embarques.",
            "producao",
        )

    configuracoes = {
        item.cultura_id: item
        for item in ConfiguracaoCultura.objects.select_related("cultura")
    }
    por_cultura = saldos_graos.values("cultura_id", "cultura__nome").annotate(
        total=Sum("quantidade_kg")
    )
    for item in por_cultura:
        config = configuracoes.get(item["cultura_id"])
        minimo = config.estoque_minimo_kg if config else Decimal("0")
        saldo = item["total"] or Decimal("0")
        if minimo > 0 and saldo < minimo:
            adicionar(
                f"producao_estoque_minimo_{item['cultura_id']}",
                "atencao",
                f"Estoque de {item['cultura__nome']} abaixo do mínimo",
                f"Saldo atual: {saldo:.3f} kg; mínimo configurado: {minimo:.3f} kg.",
                "Revisar compromissos, recebimentos previstos e disponibilidade física antes de novos embarques.",
                "producao",
            )

    safras = list(
        recebimentos.values("safra__nome")
        .annotate(total=Sum("peso_liquido_kg"))
        .order_by("-safra__nome")[:2]
    )
    if len(safras) == 2:
        atual, anterior = safras
        diferenca = (atual["total"] or Decimal("0")) - (anterior["total"] or Decimal("0"))
        adicionar(
            "producao_comparativo_safras",
            "informativo",
            "Comparativo entre safras",
            f"{atual['safra__nome']}: {atual['total']:.3f} kg; {anterior['safra__nome']}: {anterior['total']:.3f} kg; diferença: {diferenca:.3f} kg.",
            "Avaliar a diferença juntamente com área colhida, clima e produtividade por talhão.",
            "producao",
        )

    produtividade = []
    previsoes = []
    grupos = recebimentos.exclude(talhao=None).values(
        "talhao_id",
        "talhao__nome",
        "talhao__area_hectares",
        "talhao__produtividade_esperada",
        "cultura__peso_saca_kg",
    ).annotate(
        total_sacas=Sum("quantidade_sacas"),
        total_kg=Sum("peso_liquido_kg"),
    )
    for item in grupos:
        area = Decimal(str(item["talhao__area_hectares"] or 0))
        if area <= 0:
            continue
        resultado = (item["total_sacas"] or Decimal("0")) / area
        produtividade.append((resultado, item["talhao__nome"]))
        esperado_sc = Decimal(str(item["talhao__produtividade_esperada"] or 0))
        peso_saca = Decimal(str(item["cultura__peso_saca_kg"] or 60))
        if esperado_sc > 0:
            esperado_kg = area * esperado_sc * peso_saca
            realizado_kg = item["total_kg"] or Decimal("0")
            previsoes.append((item["talhao__nome"], esperado_kg, realizado_kg))

    if produtividade:
        produtividade.sort(key=lambda item: item[0])
        menor, maior = produtividade[0], produtividade[-1]
        adicionar(
            "producao_produtividade_talhoes",
            "informativo",
            "Produtividade por talhão",
            f"Maior: {maior[1]} com {maior[0]:.2f} sc/ha; menor: {menor[1]} com {menor[0]:.2f} sc/ha.",
            "Investigar diferenças de solo, manejo, clima e histórico antes de alterar o planejamento.",
            "producao",
        )

    if previsoes:
        previsto = sum((item[1] for item in previsoes), start=Decimal("0"))
        realizado = sum((item[2] for item in previsoes), start=Decimal("0"))
        diferenca_percentual = (
            (realizado - previsto) / previsto * Decimal("100")
            if previsto > 0
            else Decimal("0")
        )
        adicionar(
            "producao_prevista_realizada",
            "informativo",
            "Produção prevista x realizada",
            f"Prevista: {previsto:.3f} kg; realizada: {realizado:.3f} kg; diferença: {diferenca_percentual:.2f}%.",
            "Revisar as expectativas por talhão e registrar justificativas para desvios relevantes.",
            "producao",
        )

    for recebimento in recebimentos.select_related("cultura").order_by("-umidade_percentual")[:10]:
        config = configuracoes.get(recebimento.cultura_id)
        limite = config.umidade_alerta_percentual if config else Decimal("14")
        if recebimento.umidade_percentual > limite:
            adicionar(
                f"producao_umidade_{recebimento.id}",
                "atencao",
                f"Umidade elevada em {recebimento.cultura.nome}",
                f"Recebimento {recebimento.id}: {recebimento.umidade_percentual}% para limite configurado de {limite}%.",
                "Revisar secagem, armazenagem, descontos e condições contratuais antes da comercialização.",
                "producao",
            )

    saldo_contratos = Decimal("0")
    alertas_contrato = []
    for contrato in contratos:
        embarcado = sum(
            (
                embarque.quantidade_kg
                for embarque in contrato.embarques.all()
                if embarque.status == EmbarqueProducao.Status.CONFIRMADO
            ),
            start=Decimal("0"),
        )
        restante = max(contrato.quantidade_kg - embarcado, Decimal("0"))
        saldo_contratos += restante
        percentual_restante = (
            restante / contrato.quantidade_kg * Decimal("100")
            if contrato.quantidade_kg
            else Decimal("0")
        )
        if percentual_restante <= Decimal("10"):
            alertas_contrato.append((percentual_restante, contrato, restante))
    for percentual, contrato, restante in sorted(alertas_contrato, key=lambda item: item[0])[:5]:
        adicionar(
            f"producao_contrato_limite_{contrato.id}",
            "atencao",
            "Contrato próximo do limite",
            f"Contrato {contrato.numero}: {percentual:.2f}% restante, equivalente a {restante:.3f} kg.",
            "Conferir romaneios, tolerância, notas fiscais e saldo físico antes do próximo embarque.",
            "producao",
        )

    livre = estoque_graos - saldo_contratos
    if livre > 0:
        culturas = list(
            saldos_graos.filter(quantidade_kg__gt=0)
            .values("cultura__nome")
            .annotate(total=Sum("quantidade_kg"))
            .order_by("-total")
        )
        referencia = ""
        if culturas:
            nome = str(culturas[0]["cultura__nome"]).lower()
            produto = next((codigo for termo, codigo in PRODUCT_CODES.items() if termo in nome), None)
            cotacao = (
                CotacaoMercado.objects.filter(produto=produto).order_by("-data").first()
                if produto
                else None
            )
            if cotacao:
                referencia = (
                    f" A referência global mais recente cadastrada para {cotacao.get_produto_display()} "
                    f"é {cotacao.valor} {cotacao.unidade}, em {cotacao.data}."
                )
        adicionar(
            "producao_sugestao_comercializacao",
            "informativo",
            "Estoque sem cobertura contratual identificado",
            f"Há aproximadamente {livre:.3f} kg acima do saldo dos contratos abertos.{referencia}",
            "Avaliar qualidade, necessidade de caixa, preço local, câmbio, base regional e risco antes de comercializar.",
            "producao",
        )

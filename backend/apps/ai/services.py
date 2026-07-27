from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from apps.clima.models import PrevisaoClima
from apps.estoque.models import LoteEstoque
from apps.estoque.services import resumo_estoque
from apps.financeiro.models import LancamentoFinanceiro
from apps.maquinas.models import ManutencaoMaquina
from apps.producao.models import (
    ContratoProducao,
    EmbarqueProducao,
    OperacaoAgricola,
    RecebimentoProducao,
    SaldoGraos,
)


def gerar_insights(*, propriedade=None, safra="", propriedades=None):
    hoje = timezone.localdate()
    insights = []

    def adicionar(codigo, nivel, titulo, evidencia, recomendacao, modulo):
        insights.append(
            {
                "codigo": codigo,
                "nivel": nivel,
                "titulo": titulo,
                "evidencia": evidencia,
                "recomendacao": recomendacao,
                "modulo": modulo,
            }
        )

    financeiros = LancamentoFinanceiro.objects.filter(
        status="pendente",
        data_vencimento__lt=hoje,
    )
    operacoes = OperacaoAgricola.objects.filter(
        status="planejada",
        data_planejada__lt=hoje,
    )
    manutencoes = ManutencaoMaquina.objects.filter(
        status="agendada",
        data_prevista__lt=hoje,
    )
    clima = PrevisaoClima.objects.filter(
        data__gte=hoje,
        alerta_agricola__gt="",
    )
    lotes = LoteEstoque.objects.select_related("produto", "local")
    recebimentos = RecebimentoProducao.objects.filter(
        status=RecebimentoProducao.Status.CONFIRMADO,
    ).select_related("talhao", "cultura", "safra", "propriedade")
    saldos_graos = SaldoGraos.objects.select_related("cultura", "safra", "propriedade")
    contratos = ContratoProducao.objects.filter(
        status=ContratoProducao.Status.ABERTO,
    ).prefetch_related("embarques")

    if propriedades is not None:
        ids = list(propriedades)
        financeiros = financeiros.filter(propriedade_id__in=ids)
        operacoes = operacoes.filter(talhao__propriedade_id__in=ids)
        manutencoes = manutencoes.filter(maquina__propriedade_id__in=ids)
        clima = clima.filter(propriedade_id__in=ids)
        lotes = lotes.filter(local__propriedade_id__in=ids)
        recebimentos = recebimentos.filter(propriedade_id__in=ids)
        saldos_graos = saldos_graos.filter(propriedade_id__in=ids)
        contratos = contratos.filter(propriedade_id__in=ids)
    if propriedade:
        financeiros = financeiros.filter(propriedade_id=propriedade)
        operacoes = operacoes.filter(talhao__propriedade_id=propriedade)
        manutencoes = manutencoes.filter(maquina__propriedade_id=propriedade)
        clima = clima.filter(propriedade_id=propriedade)
        lotes = lotes.filter(local__propriedade_id=propriedade)
        recebimentos = recebimentos.filter(propriedade_id=propriedade)
        saldos_graos = saldos_graos.filter(propriedade_id=propriedade)
        contratos = contratos.filter(propriedade_id=propriedade)
    if safra:
        financeiros = financeiros.filter(safra=safra)
        operacoes = operacoes.filter(talhao__safra=safra)
        recebimentos = recebimentos.filter(safra__nome=safra)
        saldos_graos = saldos_graos.filter(safra__nome=safra)
        contratos = contratos.filter(safra__nome=safra)

    if financeiros.exists():
        adicionar(
            "financeiro_atrasado",
            "critico",
            "Contas vencidas exigem atenção",
            f"{financeiros.count()} lançamento(s) financeiro(s) estão vencidos.",
            "Revisar os vencimentos e registrar pagamento, recebimento ou renegociação.",
            "financeiro",
        )
    estoque = resumo_estoque(
        lotes,
        propriedade=propriedade,
        safra=safra,
    )
    if estoque["lotes_vencidos"]:
        adicionar(
            "estoque_vencido",
            "critico",
            "Há lotes vencidos com saldo",
            f"{estoque['lotes_vencidos']} lote(s) vencido(s) ainda possuem saldo.",
            "Bloquear o uso e avaliar descarte conforme orientação técnica e legal.",
            "estoque",
        )
    if estoque["itens_abaixo_minimo"]:
        adicionar(
            "estoque_minimo",
            "atencao",
            "Estoque abaixo do mínimo",
            f"{estoque['itens_abaixo_minimo']} item(ns) estão abaixo do limite configurado.",
            "Revisar o planejamento de compras antes das próximas operações.",
            "estoque",
        )
    if operacoes.exists():
        adicionar(
            "operacao_atrasada",
            "atencao",
            "Operações planejadas estão atrasadas",
            f"{operacoes.count()} operação(ões) têm data passada e continuam planejadas.",
            "Reprogramar, iniciar ou cancelar as operações conforme a situação de campo.",
            "operacoes",
        )
    if manutencoes.exists():
        adicionar(
            "manutencao_atrasada",
            "atencao",
            "Manutenções estão atrasadas",
            f"{manutencoes.count()} manutenção(ões) agendada(s) ultrapassaram a data.",
            "Avaliar a disponibilidade e concluir a manutenção antes de novo uso intensivo.",
            "maquinas",
        )
    for previsao in clima[:3]:
        adicionar(
            f"clima_{previsao.id}",
            "atencao",
            f"Alerta climático em {previsao.propriedade.nome}",
            f"{previsao.data}: {previsao.alerta_agricola}",
            "Confirmar a previsão atual antes de executar atividades sensíveis ao clima.",
            "clima",
        )

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
    for item in recebimentos.exclude(talhao=None).values(
        "talhao_id", "talhao__nome", "talhao__area_hectares"
    ).annotate(total_sacas=Sum("quantidade_sacas")):
        area = Decimal(str(item["talhao__area_hectares"] or 0))
        if area > 0:
            produtividade.append((item["total_sacas"] / area, item["talhao__nome"]))
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

    maior_umidade = recebimentos.order_by("-umidade_percentual").first()
    if maior_umidade and maior_umidade.umidade_percentual > 0:
        adicionar(
            "producao_qualidade_umidade",
            "informativo",
            "Maior umidade registrada",
            f"{maior_umidade.umidade_percentual}% no recebimento {maior_umidade.id} de {maior_umidade.cultura.nome}.",
            "Comparar com os limites do contrato ou do armazenador antes de classificar como não conformidade.",
            "producao",
        )

    saldo_contratos = Decimal("0")
    contrato_mais_utilizado = None
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
        percentual = embarcado / contrato.quantidade_kg * Decimal("100") if contrato.quantidade_kg else Decimal("0")
        if contrato_mais_utilizado is None or percentual > contrato_mais_utilizado[0]:
            contrato_mais_utilizado = (percentual, contrato, restante)
    if contrato_mais_utilizado:
        percentual, contrato, restante = contrato_mais_utilizado
        adicionar(
            "producao_contrato_utilizacao",
            "informativo",
            "Contrato com maior utilização",
            f"Contrato {contrato.numero}: {percentual:.2f}% utilizado e {restante:.3f} kg restantes.",
            "Planejar os próximos embarques considerando prazo, tolerância e saldo físico autorizado.",
            "producao",
        )

    livre = estoque_graos - saldo_contratos
    if livre > 0:
        adicionar(
            "producao_sugestao_comercializacao",
            "informativo",
            "Estoque sem cobertura contratual identificado",
            f"Há aproximadamente {livre:.3f} kg acima do saldo dos contratos abertos no filtro atual.",
            "Avaliar qualidade, necessidade de caixa, risco de preço e condições de mercado antes de comercializar.",
            "producao",
        )

    if not insights:
        adicionar(
            "sem_alertas",
            "informativo",
            "Nenhum alerta prioritário identificado",
            "As regras atuais não encontraram pendências críticas.",
            "Manter os dados atualizados e revisar o painel regularmente.",
            "geral",
        )
    ordem = {"critico": 0, "atencao": 1, "informativo": 2}
    insights.sort(key=lambda item: ordem[item["nivel"]])
    return {
        "gerado_em": timezone.now(),
        "metodo": "regras_explicaveis_v1",
        "insights": insights,
        "aviso": (
            "Apoio gerencial automatizado. Não substitui avaliação agronômica, "
            "mecânica, contábil, comercial ou legal."
        ),
    }

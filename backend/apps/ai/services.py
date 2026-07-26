from django.utils import timezone

from apps.clima.models import PrevisaoClima
from apps.estoque.models import LoteEstoque
from apps.estoque.services import resumo_estoque
from apps.financeiro.models import LancamentoFinanceiro
from apps.maquinas.models import ManutencaoMaquina
from apps.producao.models import (
    ContratoProducao,
    OperacaoAgricola,
    RecebimentoProducao,
    SaldoGraos,
)

from .production_insights import adicionar_insights_producao


def gerar_insights(
    *,
    propriedade=None,
    safra="",
    propriedades=None,
    cadpros=None,
):
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
    ).select_related("talhao", "cultura", "safra", "propriedade", "cadpro")
    saldos_graos = SaldoGraos.objects.select_related(
        "cultura",
        "safra",
        "propriedade",
        "cadpro",
    )
    contratos = ContratoProducao.objects.filter(
        status=ContratoProducao.Status.ABERTO,
    ).select_related("cultura", "safra", "propriedade", "cadpro").prefetch_related("embarques")

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
    if cadpros is not None:
        cadpro_ids = list(cadpros)
        recebimentos = recebimentos.filter(cadpro_id__in=cadpro_ids)
        saldos_graos = saldos_graos.filter(cadpro_id__in=cadpro_ids)
        contratos = contratos.filter(cadpro_id__in=cadpro_ids)
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

    adicionar_insights_producao(
        adicionar=adicionar,
        recebimentos=recebimentos,
        saldos_graos=saldos_graos,
        contratos=contratos,
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
        "metodo": "regras_explicaveis_v3",
        "insights": insights,
        "aviso": (
            "Apoio gerencial automatizado. Não substitui avaliação agronômica, "
            "mecânica, contábil, comercial ou legal."
        ),
    }

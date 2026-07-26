from django.utils import timezone

from apps.clima.models import PrevisaoClima
from apps.estoque.services import resumo_estoque
from apps.financeiro.models import LancamentoFinanceiro
from apps.maquinas.models import ManutencaoMaquina
from apps.producao.models import OperacaoAgricola


def gerar_insights(*, propriedade=None, safra=""):
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
        status="pendente", data_vencimento__lt=hoje
    )
    operacoes = OperacaoAgricola.objects.filter(
        status="planejada", data_planejada__lt=hoje
    )
    manutencoes = ManutencaoMaquina.objects.filter(
        status="agendada", data_prevista__lt=hoje
    )
    clima = PrevisaoClima.objects.filter(
        data__gte=hoje, alerta_agricola__gt=""
    )
    if propriedade:
        financeiros = financeiros.filter(propriedade_id=propriedade)
        operacoes = operacoes.filter(talhao__propriedade_id=propriedade)
        manutencoes = manutencoes.filter(maquina__propriedade_id=propriedade)
        clima = clima.filter(propriedade_id=propriedade)
    if safra:
        financeiros = financeiros.filter(safra=safra)
        operacoes = operacoes.filter(talhao__safra=safra)

    if financeiros.exists():
        adicionar(
            "financeiro_atrasado",
            "critico",
            "Contas vencidas exigem atenção",
            f"{financeiros.count()} lançamento(s) financeiro(s) estão vencidos.",
            "Revisar os vencimentos e registrar pagamento, recebimento ou renegociação.",
            "financeiro",
        )
    estoque = resumo_estoque(propriedade=propriedade, safra=safra)
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
            "mecânica, contábil ou legal."
        ),
    }

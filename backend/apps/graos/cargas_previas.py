"""Prévia somente leitura; a validação transacional do cancelamento continua definitiva."""
from collections import defaultdict
from decimal import Decimal
from .models import MovimentacaoGraos, PosicaoSaldoGraos


def previa_cancelamento_carga(carga):
    movimentos = list(MovimentacaoGraos.objects.filter(rateio_carga_colhida__carga=carga).select_related("posicao", "movimento_estorno")) or [carga.movimentacao]
    reducoes = defaultdict(lambda: Decimal("0"))
    for movimento in movimentos:
        if not hasattr(movimento, "movimento_estorno"):
            reducoes[movimento.posicao_id] += movimento.delta_fisico_kg
    efeitos = []
    impedimentos = []
    if carga.status != "ativa":
        impedimentos.append("Esta carga já foi encerrada. Consulte o histórico.")
    for posicao in PosicaoSaldoGraos.objects.select_related("propriedade", "cad_pro").filter(pk__in=reducoes):
        posterior = posicao.saldo_fisico_kg - reducoes[posicao.pk]
        disponivel = posterior - posicao.saldo_comprometido_kg
        bloqueada = posterior < 0 or disponivel < 0
        efeitos.append({"posicao": posicao.pk, "propriedade": posicao.propriedade.nome if posicao.propriedade else "Produção histórica", "cad_pro": posicao.cad_pro.codigo, "cultura": posicao.cultura,
                       "saldo_anterior_kg": str(posicao.saldo_fisico_kg), "saldo_posterior_kg": str(posterior), "comprometido_kg": str(posicao.saldo_comprometido_kg), "disponivel_posterior_kg": str(disponivel), "bloqueada": bloqueada})
        if bloqueada:
            impedimentos.append(f"Saldo insuficiente em {efeitos[-1]['propriedade']} / CAD/PRO {posicao.cad_pro.codigo}. Reveja vendas, reservas ou transferências posteriores antes de excluir a carga.")
    transferencias = []
    bloqueadas = [item["posicao"] for item in efeitos if item["bloqueada"]]
    saidas = list(MovimentacaoGraos.objects.filter(posicao_id__in=bloqueadas, operacao="transferencia_saida", movimento_estorno__isnull=True).order_by("-id")[:21])
    for saida in saidas[:20]:
        entrada = MovimentacaoGraos.objects.select_related("posicao__propriedade").filter(origem_id=saida.origem_id, operacao="transferencia_entrada").first()
        if entrada:
            transferencias.append({"movimento_saida": saida.pk, "quantidade_kg": str(saida.quantidade_kg), "destino": entrada.posicao.propriedade.nome if entrada.posicao.propriedade else "Produção histórica"})
    return {"carga": carga.pk, "pode_excluir": not impedimentos, "efeitos": efeitos, "impedimentos": impedimentos, "transferencias": transferencias, "mais_transferencias": len(saidas) > 20}

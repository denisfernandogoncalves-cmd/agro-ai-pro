from decimal import Decimal

from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone

from apps.estoque.models import LoteEstoque
from apps.estoque.services import resumo_estoque
from apps.financeiro.models import LancamentoFinanceiro
from apps.financeiro.services import resumo_financeiro
from apps.maquinas.models import Maquina, ManutencaoMaquina
from apps.producao.models import OperacaoAgricola
from apps.propriedades.models import Propriedade
from apps.talhoes.models import Talhao


def _decimal(valor):
    return valor or Decimal("0")


def dashboard_gerencial(*, propriedade=None, safra="", propriedades=None):
    propriedades_qs = Propriedade.objects.all()
    lancamentos = LancamentoFinanceiro.objects.all()
    operacoes = OperacaoAgricola.objects.select_related("talhao__propriedade")
    talhoes = Talhao.objects.all()
    maquinas = Maquina.objects.all()
    lotes = LoteEstoque.objects.select_related("produto", "local")

    if propriedades is not None:
        ids = list(propriedades)
        propriedades_qs = propriedades_qs.filter(pk__in=ids)
        lancamentos = lancamentos.filter(propriedade_id__in=ids)
        operacoes = operacoes.filter(talhao__propriedade_id__in=ids)
        talhoes = talhoes.filter(propriedade_id__in=ids)
        maquinas = maquinas.filter(propriedade_id__in=ids)
        lotes = lotes.filter(local__propriedade_id__in=ids)
    if propriedade:
        propriedades_qs = propriedades_qs.filter(pk=propriedade)
        lancamentos = lancamentos.filter(propriedade_id=propriedade)
        operacoes = operacoes.filter(talhao__propriedade_id=propriedade)
        talhoes = talhoes.filter(propriedade_id=propriedade)
        maquinas = maquinas.filter(propriedade_id=propriedade)
        lotes = lotes.filter(local__propriedade_id=propriedade)
    if safra:
        lancamentos = lancamentos.filter(safra=safra)
        operacoes = operacoes.filter(talhao__safra=safra)
        talhoes = talhoes.filter(safra=safra)

    financeiro = resumo_financeiro(lancamentos)
    estados = {
        item["status"]: item["total"]
        for item in operacoes.values("status").annotate(total=Count("id"))
    }
    custos = operacoes.aggregate(
        estimado=Sum("custo_estimado"),
        realizado=Sum("custo_realizado"),
    )
    meses = (
        lancamentos.filter(status=LancamentoFinanceiro.Status.LIQUIDADO)
        .annotate(mes=TruncMonth("data_liquidacao"))
        .values("mes", "tipo")
        .annotate(total=Sum("valor_liquidado"))
        .order_by("mes")
    )
    fluxo = {}
    for item in meses:
        chave = item["mes"].isoformat()[:7]
        fluxo.setdefault(
            chave,
            {"mes": chave, "entradas": Decimal("0"), "saidas": Decimal("0")},
        )
        campo = (
            "entradas"
            if item["tipo"] == LancamentoFinanceiro.Tipo.RECEBER
            else "saidas"
        )
        fluxo[chave][campo] = item["total"]

    estoque = resumo_estoque(
        lotes,
        propriedade=propriedade,
        safra=safra,
    )
    return {
        "gerado_em": timezone.now(),
        "filtros": {"propriedade": propriedade, "safra": safra},
        "estrutura": {
            "propriedades": propriedades_qs.count(),
            "talhoes": talhoes.count(),
            "area_talhoes": _decimal(
                talhoes.aggregate(total=Sum("area_hectares"))["total"]
            ),
        },
        "financeiro": financeiro,
        "estoque": estoque,
        "operacoes": {
            "total": operacoes.count(),
            "planejadas": estados.get("planejada", 0),
            "em_execucao": estados.get("em_execucao", 0),
            "concluidas": estados.get("concluida", 0),
            "canceladas": estados.get("cancelada", 0),
            "custo_estimado": _decimal(custos["estimado"]),
            "custo_realizado": _decimal(custos["realizado"]),
        },
        "maquinas": {
            "total": maquinas.count(),
            "ativas": maquinas.filter(status=Maquina.Status.ATIVA).count(),
            "em_manutencao": maquinas.filter(
                status=Maquina.Status.MANUTENCAO
            ).count(),
            "manutencoes_pendentes": ManutencaoMaquina.objects.filter(
                maquina__in=maquinas,
                status=ManutencaoMaquina.Status.AGENDADA,
            ).count(),
        },
        "fluxo_mensal": list(fluxo.values()),
    }

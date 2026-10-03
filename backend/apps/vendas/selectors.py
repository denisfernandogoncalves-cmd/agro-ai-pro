from django.db.models import Prefetch

from .models import AlteracaoVendaGraos, DevolucaoVendaGraos, EntregaVendaGraos, VendaGraos


def selecionar_vendas():
    return VendaGraos.objects.select_related(
        "posicao",
        "posicao__cad_pro",
        "posicao__armazem",
        "posicao__propriedade",
        "lote",
        "reserva",
        "criado_por",
        "rateio_particular",
    ).prefetch_related(
        Prefetch("alteracoes", queryset=AlteracaoVendaGraos.objects.select_related("criado_por")),
        Prefetch(
            "entregas",
            queryset=EntregaVendaGraos.objects.select_related("movimentacao"),
        ),
        Prefetch(
            "devolucoes",
            queryset=DevolucaoVendaGraos.objects.select_related("movimentacao"),
        ),
    )


def selecionar_entregas():
    return EntregaVendaGraos.objects.filter(cancelado_em__isnull=True, venda__excluida_em__isnull=True).select_related(
        "venda",
        "venda__posicao",
        "venda__posicao__cad_pro",
        "venda__posicao__armazem",
        "venda__posicao__propriedade",
        "movimentacao",
    )

from django.db.models import Prefetch

from .models import DevolucaoVendaGraos, EntregaVendaGraos, VendaGraos


def selecionar_vendas():
    return VendaGraos.objects.select_related(
        "posicao",
        "posicao__cad_pro",
        "posicao__armazem",
        "posicao__armazem__propriedade",
        "lote",
        "reserva",
        "criado_por",
    ).prefetch_related(
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
    return EntregaVendaGraos.objects.select_related(
        "venda",
        "venda__posicao",
        "venda__posicao__cad_pro",
        "venda__posicao__armazem",
        "venda__posicao__armazem__propriedade",
        "movimentacao",
    )

from django.db.models import Prefetch

from apps.graos.models import CargaColhida

from .models import DevolucaoVendaGraos, EntregaVendaGraos, VendaGraos


def selecionar_vendas():
    cargas = CargaColhida.objects.select_related("grupo_colheita").order_by(
        "-data_colheita", "-id"
    )
    return VendaGraos.objects.select_related(
        "posicao",
        "posicao__cad_pro",
        "posicao__armazem",
        "posicao__armazem__propriedade",
        "lote",
        "reserva",
        "criado_por",
    ).prefetch_related(
        Prefetch("lote__cargas_colhidas", queryset=cargas),
        Prefetch(
            "entregas",
            queryset=EntregaVendaGraos.objects.select_related("movimentacao"),
        ),
        Prefetch(
            "devolucoes",
            queryset=DevolucaoVendaGraos.objects.select_related("movimentacao"),
        ),
    )


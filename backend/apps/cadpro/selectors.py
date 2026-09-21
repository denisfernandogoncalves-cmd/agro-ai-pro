from .models import CADPro, CADProPropriedade


def selecionar_cadpros():
    return CADPro.objects.all()


def selecionar_vinculos(cad_pro_id, *, somente_ativos=True):
    queryset = CADProPropriedade.objects.select_related(
        "cad_pro",
        "propriedade",
    ).filter(cad_pro_id=cad_pro_id)
    if somente_ativos:
        queryset = queryset.filter(ativo=True)
    return queryset

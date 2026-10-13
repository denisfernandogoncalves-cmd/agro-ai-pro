from django.db.models import Sum, Q, F, Case, When, IntegerField
from django.db.models.functions import TruncWeek, TruncMonth
from apps.financeiro.models import ParceiroFinanceiro

def agrupar_financeiro(qs, modo, pagina=1, por_pagina=25):
    if not modo: return None
    if modo=="fornecedor":
        expr=Case(When(parceiro_id__isnull=True,then=-F("id")),default=F("parceiro_id"),output_field=IntegerField())
    else:
        expr=TruncWeek("data_vencimento") if modo=="semana" else TruncMonth("data_vencimento") if modo=="mes" else F("data_vencimento")
    grupos=qs.order_by().annotate(grupo=expr).values("grupo","tipo").annotate(pendente=Sum("valor",filter=Q(status="pendente")),realizado=Sum("valor_liquidado",filter=Q(status="liquidado")),cancelado=Sum("valor",filter=Q(status="cancelado"))).order_by("grupo","tipo")
    total=grupos.count();linhas=list(grupos[(pagina-1)*por_pagina:pagina*por_pagina]);nomes={}
    if modo=="fornecedor":
        nomes=dict(ParceiroFinanceiro.objects.filter(pk__in=[r["grupo"] for r in linhas if r["grupo"]>0]).values_list("id","nome"))
    for row in linhas:
        grupo=row.pop("grupo")
        row["referencia"]=nomes.get(grupo,f"Sem parceiro cadastrado · título #{-grupo}") if modo=="fornecedor" else str(grupo.date() if hasattr(grupo,"date") else grupo)
        for campo in ["pendente","realizado","cancelado"]:row[campo]=str(row[campo] or 0)
    return {"modo":modo,"pagina":pagina,"total":total,"total_paginas":(total+por_pagina-1)//por_pagina,"resultados":linhas,"base":"Período por vencimento; realizado usa valor liquidado. Semana inicia segunda-feira. Fornecedores por ID; títulos sem parceiro permanecem separados."}


def vencimentos_financeiros(qs):
    from datetime import timedelta
    from django.utils import timezone
    hoje=timezone.localdate()
    pendentes=qs.filter(status="pendente",tipo="pagar")
    faixas=[("A vencer",Q(data_vencimento__gt=hoje)),("Vence hoje",Q(data_vencimento=hoje)),("1 a 7 dias em atraso",Q(data_vencimento__lt=hoje,data_vencimento__gte=hoje-timedelta(days=7))),("8 a 30 dias em atraso",Q(data_vencimento__lt=hoje-timedelta(days=7),data_vencimento__gte=hoje-timedelta(days=30))),("Mais de 30 dias em atraso",Q(data_vencimento__lt=hoje-timedelta(days=30)))]
    from django.db.models import Count
    agregado=pendentes.aggregate(**{f"{campo}{i}":expr for i,(_,filtro) in enumerate(faixas) for campo,expr in [("valor",Sum("valor",filter=filtro)),("quantidade",Count("id",filter=filtro))]})
    return {"data_base":hoje.isoformat(),"base":"Títulos a pagar pendentes; faixas descritivas por vencimento, sem criar prazos obrigatórios.","faixas":[{"descricao":nome,"valor":str(agregado[f"valor{i}"] or 0),"quantidade":agregado[f"quantidade{i}"]} for i,(nome,_) in enumerate(faixas)]}

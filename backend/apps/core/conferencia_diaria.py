from decimal import Decimal
from django.db.models import Sum
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.accounts.access import pode
from apps.accounts.views import NoStoreResponseMixin
from apps.graos.models import ArmazemGraos,MovimentacaoGraos,ConferenciaEstoque
from apps.graos.historico_terceiros import periodo_terceiros

class Filtros(serializers.Serializer):
    armazem=serializers.PrimaryKeyRelatedField(queryset=ArmazemGraos.objects.all())
    cultura=serializers.CharField(max_length=50)
    safra=serializers.CharField(max_length=20)
    data=serializers.DateField()
    pagina_contagens=serializers.IntegerField(min_value=1,max_value=1000000,default=1)

class ConferenciaDiariaView(NoStoreResponseMixin,APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request):
        if not pode(request.user,"producao-saldos","consultar"):
            raise PermissionDenied("Consulta de saldos necessária.")
        f=Filtros(data=request.query_params);f.is_valid(raise_exception=True);d=f.validated_data
        day=d["data"];warehouse=d["armazem"]
        qs=MovimentacaoGraos.objects.filter(posicao__armazem=warehouse,posicao__cultura__iexact=d["cultura"],posicao__safra__iexact=d["safra"])
        opening=qs.filter(data_movimento__lt=day).aggregate(v=Sum("delta_fisico_kg"))["v"] or Decimal("0")
        rows=qs.filter(data_movimento=day)
        change=rows.aggregate(v=Sum("delta_fisico_kg"))["v"] or Decimal("0")
        third=periodo_terceiros(warehouse,d["cultura"],d["safra"],day)
        third_open=sum((delta for _,date,delta in third if date<day),Decimal("0"))
        third_change=sum((delta for _,date,delta in third if date==day),Decimal("0"))
        groups=list(rows.values("operacao").annotate(delta_kg=Sum("delta_fisico_kg")).order_by("operacao"))
        counts_qs=ConferenciaEstoque.objects.filter(armazem=warehouse,cultura__iexact=d["cultura"],safra__iexact=d["safra"],data_contagem__lte=day).select_related("criado_por").order_by("-data_contagem","-id")
        offset=(d["pagina_contagens"]-1)*25
        counts=list(counts_qs[offset:offset+26])
        comparacao=[]
        baseline=counts[25] if len(counts)>25 else None
        previous=None if baseline is None else baseline.contado_kg-baseline.saldo_proprio_kg-baseline.saldo_terceiros_kg
        for count in reversed(counts[:25]):
            difference=count.contado_kg-count.saldo_proprio_kg-count.saldo_terceiros_kg
            comparacao.append({"id":count.pk,"data":count.data_contagem,"contado_kg":str(count.contado_kg),"saldo_registrado_kg":str(count.saldo_proprio_kg+count.saldo_terceiros_kg),"diferenca_kg":str(difference),"variacao_diferenca_kg":None if previous is None else str(difference-previous),"responsavel":count.criado_por.get_username(),"justificativa":count.justificativa})
            previous=difference
        return Response({"armazem":warehouse.pk,"armazem_nome":warehouse.nome,"cultura":d["cultura"],"safra":d["safra"],"data":day,"abertura_propria_kg":str(opening),"abertura_terceiros_kg":str(third_open),"movimento_proprio_kg":str(change),"movimento_terceiros_kg":str(third_change),"saldo_final_proprio_kg":str(opening+change),"saldo_final_terceiros_kg":str(third_open+third_change),"saldo_final_fisico_kg":str(opening+change+third_open+third_change),"movimentos_saldo":groups,"contagens":comparacao,"contagens_total":counts_qs.count(),"pagina_contagens":d["pagina_contagens"],"gerado_em":timezone.now(),"base":"Consulta por data dos movimentos. Movimentos internos podem compensar entre origens/CAD-PROs; não representam necessariamente caminhões recebidos ou expedidos. Saldos negativos são exibidos para conferência. Contagens são snapshots originais, sem ajuste ou fechamento automático."})

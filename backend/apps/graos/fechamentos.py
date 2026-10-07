import hashlib
import json
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum
from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.accounts.access import pode
from apps.accounts.views import NoStoreResponseMixin
from .models import ArmazemGraos, FechamentoPeriodo, MovimentacaoGraos, MovimentoProducaoTerceiro


def movimentos_periodo(armazem, cultura, safra, fim):
    filtros={"armazem":armazem,"cultura__iexact":cultura,"safra__iexact":safra}
    proprio=MovimentacaoGraos.objects.filter(data_movimento__lte=fim, **{f"posicao__{k}":v for k,v in filtros.items()})
    from .historico_terceiros import periodo_terceiros
    terceiros=periodo_terceiros(armazem,cultura,safra,fim)
    return proprio, terceiros


def assinatura_periodo(proprio, terceiros):
    valores=[list(proprio.order_by("id").values_list("id","data_movimento","delta_fisico_kg")),terceiros]
    return hashlib.sha256(json.dumps(valores,default=str).encode()).hexdigest()


def periodos_afetados(armazem, cultura, safra, datas):
    return [p for p in FechamentoPeriodo.objects.filter(armazem=armazem,cultura__iexact=cultura,safra__iexact=safra) if any(d and p.inicio<=d<=p.fim for d in datas)]


def aviso_periodo(request, entrada, data=None, novo=None):
    datas=[getattr(entrada,'data_entrada',getattr(entrada,'data_colheita',None)),data]
    periodos=periodos_afetados(entrada.armazem,entrada.cultura,entrada.safra,datas)
    if novo:
        periodos+=periodos_afetados(novo.get('armazem',entrada.armazem),novo.get('cultura',entrada.cultura),novo.get('safra',entrada.safra),datas+[novo.get('data_entrada'),novo.get('data_colheita')])
    if periodos and request.headers.get("Confirmar-Periodo-Fechado") != "sim":
        return Response({"codigo":"periodo_fechado","detail":"Este lançamento pertence a um período conferido. A alteração preservará o fechamento original e deverá ser conferida novamente.","fechamentos":[p.pk for p in periodos]},status=409)
    return None


class PeriodoFechado(APIException):
    status_code=409


def verificar_periodo(request, entrada, data=None, novo=None):
    if request is None:
        return
    aviso=aviso_periodo(request,entrada,data,novo)
    if aviso is not None:
        raise PeriodoFechado(aviso.data)
    if request.headers.get('Confirmar-Periodo-Fechado') == 'sim':
        datas=[getattr(entrada,'data_entrada',getattr(entrada,'data_colheita',None)),data]
        afetados=periodos_afetados(entrada.armazem,entrada.cultura,entrada.safra,datas)
        if novo:
            afetados+=periodos_afetados(novo.get('armazem',entrada.armazem),novo.get('cultura',entrada.cultura),novo.get('safra',entrada.safra),datas+[novo.get('data_entrada'),novo.get('data_colheita')])
        from .pendencias import registrar_pendencia
        for p in afetados:
            registrar_pendencia(request.user,f'fechamento:{p.pk}:{p.assinatura[:12]}','periodo',f'Conferir novamente fechamento #{p.pk}',{'fechamento':p.pk,'cultura':p.cultura,'safra':p.safra})


class FechamentoSerializer(serializers.Serializer):
    armazem=serializers.PrimaryKeyRelatedField(queryset=ArmazemGraos.objects.all())
    cultura=serializers.ChoiceField(choices=("Soja","Milho","Trigo"))
    safra=serializers.CharField(max_length=20)
    inicio=serializers.DateField()
    fim=serializers.DateField()
    justificativa=serializers.CharField(max_length=2000)
    chave_idempotencia=serializers.UUIDField()

    def validate(self,d):
        if d["fim"]<d["inicio"] or d["fim"]>timezone.localdate():
            raise serializers.ValidationError("Confira o período: início até fim, sem data final futura.")
        return d


def representar(p,cache=None):
    if cache is None:
        proprio, terceiros=movimentos_periodo(p.armazem,p.cultura,p.safra,p.fim)
        atual=assinatura_periodo(proprio,terceiros)
    else:
        filtro=lambda c,s,d:c.strip().casefold()==p.cultura.strip().casefold() and s.strip().casefold()==p.safra.strip().casefold() and d<=p.fim
        proprio=sorted([(pk,d,v) for c,s,pk,d,v in cache[0].get(p.armazem_id,[]) if filtro(c,s,d)],key=lambda v:v[0])
        terceiros=sorted([(pk,d,v) for pk,d,c,s,v in cache[1].get(p.armazem_id,[]) if filtro(c,s,d)],key=lambda v:v[0])
        atual=hashlib.sha256(json.dumps([proprio,terceiros],default=str).encode()).hexdigest()
    mudou=atual!=p.assinatura
    return {"id":p.pk,"armazem":p.armazem_id,"armazem_nome":p.armazem.nome,"cultura":p.cultura,"safra":p.safra,"inicio":p.inicio,"fim":p.fim,"saldo_proprio_kg":str(p.saldo_proprio_kg),"saldo_terceiros_kg":str(p.saldo_terceiros_kg),"saldo_total_kg":str(p.saldo_proprio_kg+p.saldo_terceiros_kg),"alterado":mudou,"responsavel":p.criado_por.username,"registrado_em":p.criado_em,"justificativa":p.justificativa}


class FechamentosView(NoStoreResponseMixin,APIView):
    permission_classes=(IsAuthenticated,)

    def verificar(self,user,acao):
        if not any(pode(user,m,acao) for m in ("cargas","producao-saldos")):
            raise PermissionDenied()

    def get(self,request):
        self.verificar(request.user,"consultar")
        qs=FechamentoPeriodo.objects.select_related('armazem','criado_por').order_by('-criado_em','-id')
        busca=request.query_params.get('busca','').strip()[:160]
        if busca:qs=qs.filter(Q(armazem__nome__icontains=busca)|Q(cultura__icontains=busca)|Q(safra__icontains=busca))
        pagina=serializers.IntegerField(min_value=1,max_value=1000000).run_validation(request.query_params['pagina']) if request.query_params.get('pagina') else None
        total=qs.count() if pagina else None
        periodos=list(qs[(pagina-1)*25:pagina*25] if pagina else qs[:50])
        if not periodos:return Response({'total':total,'itens':[]} if pagina else [])
        ids={p.armazem_id for p in periodos};limite=max(p.fim for p in periodos)
        from collections import defaultdict
        from .historico_terceiros import eventos_terceiros
        propios=defaultdict(list);movs=defaultdict(list)
        for a,c,s,pk,d,v in MovimentacaoGraos.objects.filter(posicao__armazem_id__in=ids,data_movimento__lte=limite).values_list('posicao__armazem_id','posicao__cultura','posicao__safra','id','data_movimento','delta_fisico_kg'):
            propios[a].append((c,s,pk,d,v))
        for m in MovimentoProducaoTerceiro.objects.filter(entrada__armazem_id__in=ids).select_related('entrada').order_by('entrada_id','id'):
            movs[m.entrada.armazem_id].append(m)
        cache=(propios,{a:list(eventos_terceiros(a,ms)) for a,ms in movs.items()})
        itens=[representar(p,cache) for p in periodos]
        return Response({'total':total,'itens':itens} if pagina else itens)

    def post(self,request):
        self.verificar(request.user,"cadastrar")
        s=FechamentoSerializer(data=request.data);s.is_valid(raise_exception=True);d=s.validated_data
        with transaction.atomic():
            ArmazemGraos.objects.select_for_update().get(pk=d["armazem"].pk)
            p=FechamentoPeriodo.objects.filter(chave_idempotencia=d["chave_idempotencia"]).first()
            if p:
                if p.criado_por_id!=request.user.pk or any(getattr(p,k)!=v for k,v in d.items()):
                    raise serializers.ValidationError("Chave já usada em outro fechamento.")
                return Response(representar(p))
            proprio, terceiros=movimentos_periodo(d["armazem"],d["cultura"],d["safra"],d["fim"])
            p=FechamentoPeriodo.objects.create(**d,saldo_proprio_kg=proprio.aggregate(v=Sum("delta_fisico_kg"))["v"] or Decimal(0),saldo_terceiros_kg=sum((v for _,_,v in terceiros),Decimal(0)),assinatura=assinatura_periodo(proprio,terceiros),criado_por=request.user)
        return Response(representar(p),status=201)

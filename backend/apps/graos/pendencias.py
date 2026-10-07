from django.db import transaction
from django.db.models import Q, Count
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.accounts.access import pode
from apps.accounts.views import NoStoreResponseMixin
from apps.core.models import RegistroAlteracao
from .models import PendenciaConferencia, CargaColhida, EntradaProducaoTerceiro, MovimentoProducaoTerceiro
from .conferencia_pesagem import alertas_pesagem


@transaction.atomic
def registrar_pendencia(usuario, referencia, tipo, titulo, detalhes):
    p,_=PendenciaConferencia.objects.get_or_create(referencia=referencia,defaults={"tipo":tipo,"titulo":titulo,"detalhes":detalhes,"responsavel":usuario})
    p=PendenciaConferencia.objects.select_for_update().get(pk=p.pk)
    if p.situacao=='resolvida':
        p.situacao='aberta';p.versao+=1;p.detalhes=detalhes;p.save()
        RegistroAlteracao.objects.create(usuario=usuario,usuario_nome=usuario.username,modulo='cargas',entidade='pendencia_conferencia',registro_id=str(p.pk),acao='editar',alteracoes={'motivo':'Reaberta por nova ocorrência','depois':{'situacao':'aberta','versao':p.versao}})
    return p


def pendencias_pesagem(obj, usuario, terceiro=False):
    origem="terceiro" if terceiro else "propria"
    contexto={"origem":origem,"armazem":obj.armazem_id,"safra":obj.safra,"placa":obj.placa,"excluir_id":obj.pk}
    contexto["depositante" if terceiro else "propriedade"]=obj.depositante if terceiro else obj.propriedade_id
    if terceiro and obj.terceiro_id:
        contexto["terceiro"]=obj.terceiro_id
    calculo={"cultura":obj.cultura,"peso_bruto_kg":obj.peso_bruto_kg,"tara_kg":obj.tara_kg}
    alertas=alertas_pesagem(contexto,calculo)
    if alertas:
        registrar_pendencia(usuario,f"{origem}:{obj.pk}:peso","peso",f"Conferir peso do romaneio #{obj.pk}",{"origem":origem,"registro":obj.pk,"alertas":alertas})
    filtros={"cultura__iexact":obj.cultura,"safra__iexact":obj.safra,"placa__iexact":obj.placa,"peso_bruto_kg":obj.peso_bruto_kg}
    if terceiro:
        filtros.update(data_entrada=obj.data_entrada)
        filtros.update({"terceiro_id":obj.terceiro_id} if obj.terceiro_id else {"depositante__iexact":obj.depositante,"terceiro__isnull":True})
        canceladas=MovimentoProducaoTerceiro.objects.filter(tipo="entrada",estorno__isnull=False).values("entrada_id")
        qs=EntradaProducaoTerceiro.objects.filter(**filtros).exclude(pk__in=canceladas)
    else:
        qs=CargaColhida.objects.filter(**filtros,propriedade_id=obj.propriedade_id,data_colheita=obj.data_colheita,status="ativa")
    duplicados=list(qs.exclude(pk=obj.pk).values_list("id",flat=True)[:10])
    if duplicados:
        registrar_pendencia(usuario,f"{origem}:{obj.pk}:duplicidade","duplicidade",f"Possível duplicidade do romaneio #{obj.pk}",{"origem":origem,"registro":obj.pk,"semelhantes":duplicados})


class PendenciaSerializer(serializers.ModelSerializer):
    responsavel_nome=serializers.CharField(source="responsavel.username",read_only=True)
    idade_dias=serializers.SerializerMethodField()
    atrasada=serializers.SerializerMethodField()
    def get_idade_dias(self,p): return (timezone.localdate()-timezone.localtime(p.criado_em).date()).days
    def get_atrasada(self,p): return p.situacao!='resolvida' and bool(p.detalhes.get('data_limite')) and p.detalhes['data_limite']<str(timezone.localdate())
    class Meta:
        model=PendenciaConferencia
        fields=("id","tipo","titulo","detalhes","situacao","versao","responsavel_nome","criado_em","atualizado_em","idade_dias","atrasada")


class AtualizarPendenciaSerializer(serializers.Serializer):
    versao=serializers.IntegerField(min_value=1)
    situacao=serializers.ChoiceField(choices=("aberta","em_analise","resolvida"))
    motivo=serializers.CharField(max_length=2000)
    assumir=serializers.BooleanField(default=False)
    prioridade=serializers.ChoiceField(choices=('alta','normal','baixa'),required=False)
    data_limite=serializers.DateField(required=False,allow_null=True)


class PendenciasView(NoStoreResponseMixin,APIView):
    permission_classes=(IsAuthenticated,)

    def verificar(self,user,acao):
        if not any(pode(user,m,acao) for m in ("cargas","producao-saldos")):
            raise PermissionDenied()

    def get(self,request,pk=None):
        self.verificar(request.user,"consultar")
        if pk is not None:
            p=get_object_or_404(PendenciaConferencia.objects.select_related('responsavel'),pk=pk)
            if p.detalhes.get('origem') in ('propria','terceiro') and not pode(request.user,'cargas','consultar'):
                raise PermissionDenied()
            historico=RegistroAlteracao.objects.filter(entidade='pendencia_conferencia',registro_id=str(pk)).order_by('id')
            return Response({**PendenciaSerializer(p).data,'historico':list(historico.values('usuario_nome','criado_em','alteracoes'))})
        situacao=request.query_params.get("situacao","aberta")
        if situacao and situacao not in ("aberta","em_analise","resolvida"):
            raise serializers.ValidationError("Situação inválida.")
        qs=PendenciaConferencia.objects.select_related("responsavel").order_by("-criado_em")
        if not pode(request.user,'cargas','consultar'):
            qs=qs.exclude(detalhes__origem__in=('propria','terceiro'))
        resumo={r['situacao']:r['n'] for r in qs.values('situacao').annotate(n=Count('id'))}
        resumo['atrasadas']=qs.exclude(situacao='resolvida').filter(detalhes__data_limite__lt=str(timezone.localdate())).count()
        if situacao:qs=qs.filter(situacao=situacao)
        busca=request.query_params.get('busca','').strip()[:160]
        if busca:qs=qs.filter(Q(titulo__icontains=busca)|Q(responsavel__username__icontains=busca)|Q(tipo__icontains=busca))
        if request.query_params.get('tipo'):qs=qs.filter(tipo=request.query_params['tipo'])
        if request.query_params.get('pagina'):
            pagina=serializers.IntegerField(min_value=1,max_value=1000000).run_validation(request.query_params['pagina'])
            return Response({'total':qs.count(),'resumo':resumo,'itens':PendenciaSerializer(qs[(pagina-1)*25:pagina*25],many=True).data})
        return Response(PendenciaSerializer(qs[:100],many=True).data)

    def patch(self,request,pk):
        self.verificar(request.user,"editar")
        s=AtualizarPendenciaSerializer(data=request.data);s.is_valid(raise_exception=True);d=s.validated_data
        with transaction.atomic():
            p=get_object_or_404(PendenciaConferencia.objects.select_for_update(),pk=pk)
            if p.detalhes.get('origem') in ('propria','terceiro') and not pode(request.user,'cargas','editar'):
                raise PermissionDenied()
            if p.versao!=d["versao"]:
                return Response({"detail":"A pendência mudou. Atualize antes de salvar."},status=409)
            antes={"situacao":p.situacao,"responsavel":p.responsavel_id,"versao":p.versao}
            antes['detalhes']=p.detalhes.copy()
            p.detalhes={**p.detalhes,**{k:str(d[k]) if d[k] is not None else None for k in ('prioridade','data_limite') if k in d}}
            p.situacao=d["situacao"]
            if d["assumir"]:p.responsavel=request.user
            p.versao+=1;p.save()
            RegistroAlteracao.objects.create(usuario=request.user,usuario_nome=request.user.username,modulo="cargas",entidade="pendencia_conferencia",registro_id=str(p.pk),acao="editar",alteracoes={"antes":antes,"depois":{"situacao":p.situacao,"responsavel":p.responsavel_id,"versao":p.versao,'detalhes':p.detalhes},"motivo":d["motivo"]})
        return Response(PendenciaSerializer(p).data)

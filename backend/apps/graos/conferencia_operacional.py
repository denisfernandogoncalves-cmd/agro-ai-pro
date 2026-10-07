"""Vínculo explícito e conciliação somente de leitura, sem ajuste de estoque."""
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from apps.accounts.access import pode
from apps.accounts.views import NoStoreResponseMixin
from .models import EntradaProducaoTerceiro, TerceiroCadastro, ArmazemGraos, MovimentacaoGraos, MovimentoProducaoTerceiro, ConferenciaEstoque
from .conferencia_estoque import saldo_estoque, representar
from .historico_terceiros import eventos_terceiros
from .terceiros import executar_terceiro, EntradaSerializer


class VinculoSerializer(serializers.Serializer):
    terceiro = serializers.PrimaryKeyRelatedField(queryset=TerceiroCadastro.objects.filter(ativo=True))
    versao = serializers.IntegerField(min_value=1)
    motivo = serializers.CharField(max_length=500)


class VinculoTerceiroView(NoStoreResponseMixin, APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request, pk):
        if not pode(request.user, 'cargas', 'editar'): raise PermissionDenied()
        s=VinculoSerializer(data=request.data);s.is_valid(raise_exception=True)
        e=get_object_or_404(EntradaProducaoTerceiro,pk=pk)
        d={**s.validated_data,'depositante':s.validated_data['terceiro'].nome,
            'armazem':e.armazem,'cultura':e.cultura,'safra':e.safra,'peso_liquido_kg':e.peso_liquido_kg}
        entrada,replay=executar_terceiro(usuario=request.user,tipo='edicao',dados=d,
            chave=request.headers.get('Idempotency-Key',''),pk=pk,request=request)
        return Response(EntradaSerializer(entrada).data,status=200 if replay else 201)


class ConciliacaoSerializer(serializers.Serializer):
    armazem=serializers.PrimaryKeyRelatedField(queryset=ArmazemGraos.objects.all())
    cultura=serializers.ChoiceField(choices=('Soja','Milho','Trigo'))
    safra=serializers.CharField(max_length=20)


class ConciliacaoEstoqueView(NoStoreResponseMixin, APIView):
    permission_classes=(IsAuthenticated,)

    @transaction.atomic
    def get(self,request):
        if not pode(request.user,'producao-saldos','consultar'): raise PermissionDenied()
        s=ConciliacaoSerializer(data=request.query_params);s.is_valid(raise_exception=True);d=s.validated_data
        ArmazemGraos.objects.select_for_update().get(pk=d['armazem'].pk)
        filtros={'armazem':d['armazem'],'cultura__iexact':d['cultura'],'safra__iexact':d['safra']}
        proprio,terceiros=saldo_estoque(d)
        movimentos=MovimentacaoGraos.objects.filter(**{'posicao__'+k:v for k,v in filtros.items()})
        grupos=list(movimentos.values('operacao','origem__metadados__tipo').annotate(delta_kg=Sum('delta_fisico_kg')))
        ledger=sum((g['delta_kg'] or Decimal(0) for g in grupos),Decimal(0))
        categorias_proprias={}
        for g in grupos:
            tipo='transferencia_terceiro' if g['origem__metadados__tipo']=='transferencia_terceiro' else g['operacao']
            categorias_proprias[tipo]=categorias_proprias.get(tipo,Decimal(0))+g['delta_kg']
        movs=list(MovimentoProducaoTerceiro.objects.filter(entrada__armazem=d['armazem']).select_related('entrada').order_by('entrada_id','id'))
        tipos={m.pk:m.tipo for m in movs};categorias={}
        for pk,_,c,safra,v in eventos_terceiros(d['armazem'],movs):
            if c.strip().casefold()==d['cultura'].casefold() and safra.strip().casefold()==d['safra'].casefold():
                tipo=tipos[pk];categorias[tipo]=categorias.get(tipo,Decimal(0))+v
        externo=sum(categorias.values(),Decimal(0))
        contagem=ConferenciaEstoque.objects.filter(**filtros).select_related('armazem','criado_por').order_by('-data_contagem','-id').first()
        return Response({'operacoes':[{'operacao':k,'delta_kg':str(v)} for k,v in categorias_proprias.items()],
            'operacoes_terceiros':[{'operacao':k,'delta_kg':str(v)} for k,v in categorias.items()],
            'saldo_proprio_kg':str(proprio),'ledger_proprio_kg':str(ledger),'diferenca_proprio_kg':str(proprio-ledger),
            'saldo_terceiros_kg':str(terceiros),'ledger_terceiros_kg':str(externo),'diferenca_terceiros_kg':str(terceiros-externo),
            'estoque_total_kg':str(proprio+terceiros),'ultima_contagem':representar(contagem) if contagem else None,
            'aviso':'Transferências internas trocam titularidade; não são produção. Diferença física refere-se ao saldo registrado no momento da contagem. Nenhum ajuste automático.'})

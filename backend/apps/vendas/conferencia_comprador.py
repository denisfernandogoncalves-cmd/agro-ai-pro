from decimal import Decimal
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.core.models import RegistroAlteracao
from apps.graos.fechamentos import periodos_afetados
from .models import ConferenciaComprador, EntregaVendaGraos

class Qualidade(serializers.Serializer):
    umidade = serializers.DecimalField(max_digits=6,decimal_places=3,min_value=0,max_value=100,required=False)
    impurezas = serializers.DecimalField(max_digits=6,decimal_places=3,min_value=0,max_value=100,required=False)
    avariados = serializers.DecimalField(max_digits=6,decimal_places=3,min_value=0,max_value=100,required=False)

class EntradaConferencia(serializers.Serializer):
    versao=serializers.IntegerField(min_value=0)
    peso_recebido_liquido_kg=serializers.DecimalField(max_digits=16,decimal_places=3,min_value=Decimal("0.001"))
    frete_realizado=serializers.DecimalField(max_digits=16,decimal_places=2,min_value=0,allow_null=True,required=False)
    qualidade=Qualidade(required=False)
    justificativa=serializers.CharField(max_length=2000,allow_blank=False)

def dados_conferencia(entrega):
    c=ConferenciaComprador.objects.filter(entrega=entrega).first()
    return {"entrega":entrega.pk,"expedido_liquido_kg":str(entrega.quantidade_kg),"peso_recebido_liquido_kg":str(c.peso_recebido_liquido_kg) if c else None,"diferenca_kg":str(c.peso_recebido_liquido_kg-entrega.quantidade_kg) if c else None,"frete_realizado":str(c.frete_realizado) if c and c.frete_realizado is not None else None,"qualidade":c.qualidade if c else {},"qualidade_origem":{"umidade":str(entrega.umidade_percentual) if entrega.umidade_percentual is not None else None,"avariados":str(entrega.avariados_percentual) if entrega.avariados_percentual is not None else None},"versao":c.versao if c else 0,"usuario":c.usuario.get_username() if c else None,"atualizado_em":c.atualizado_em if c else None,"cancelada":entrega.cancelado_em is not None,"base":"Pesos líquidos em kg; diferenças informativas, sem ajuste automático."}

class ConferenciaCompradorMixin:
    @action(detail=True,methods=["get","put"],url_path=r"entregas/(?P<entrega_id>\d+)/conferencia-comprador")
    def conferencia_comprador(self,request,pk=None,entrega_id=None):
        venda=self.get_object()
        if request.method=="GET":
            entrega=get_object_or_404(EntregaVendaGraos,venda=venda,pk=entrega_id)
            return Response(dados_conferencia(entrega))
        ser=EntradaConferencia(data=request.data);ser.is_valid(raise_exception=True)
        with transaction.atomic():
            entrega=get_object_or_404(EntregaVendaGraos.objects.select_for_update(),venda=venda,pk=entrega_id)
            if entrega.cancelado_em or venda.excluida_em or venda.status=="cancelada":
                return Response({"detail":"Entrega cancelada/excluída: conferência disponível somente para consulta."},status=409)
            p=venda.posicao
            if periodos_afetados(p.armazem,p.cultura,p.safra,[entrega.data_entrega]):
                return Response({"detail":"Período fechado: conferência protegida contra alteração."},status=409)
            before=dados_conferencia(entrega)
            if before["versao"]!=ser.validated_data["versao"]:
                return Response({"detail":"A conferência mudou. Recarregue antes de salvar."},status=409)
            d=dict(ser.validated_data);d.pop("versao");d["qualidade"]={k:str(v) for k,v in d.get("qualidade",{}).items()}
            ConferenciaComprador.objects.update_or_create(entrega=entrega,defaults={**d,"usuario":request.user,"versao":before["versao"]+1})
            after=dados_conferencia(entrega)
            RegistroAlteracao.objects.create(usuario=request.user,usuario_nome=request.user.get_username(),modulo="vendas",entidade="ConferenciaComprador",registro_id=str(entrega.pk),acao="editar" if before["versao"] else "cadastrar",alteracoes={"antes":{k:str(v) if k=="atualizado_em" else v for k,v in before.items()},"depois":{k:str(v) if k=="atualizado_em" else v for k,v in after.items()},"justificativa":d["justificativa"]})
            return Response(after)

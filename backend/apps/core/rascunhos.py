"""Rascunhos privados; campos limitados aos formulários comerciais e de produção."""
import json
from rest_framework import permissions, serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.accounts.access import pode
from apps.accounts.views import NoStoreResponseMixin
from .models import RascunhoFormulario

CAMPOS = {
 "vendas": {"formulario": {"contrato","numero_contrato","cliente_nome","posicao","quantidade_kg","data_contrato","data_limite_entrega","observacoes"},"novaSaida":{"quantidade_kg","data_movimento","destino","placa","motorista","nota_produtor","nota_empresa","observacoes"},"novaPosicao":{"propriedade","cad_pro","cultura","safra","classificacao_codigo","armazem"},"tipoLancamento":None,"origemSelecionada":None},
 "producao-saldos": {"credito":{"lote","quantidade_kg","data_movimento","referencia_externa","observacoes"}},
}

def validar_dados(contexto, dados):
    if not isinstance(dados,dict) or set(dados)-set(CAMPOS[contexto]) or len(json.dumps(dados))>20000:
        raise serializers.ValidationError("Rascunho inválido ou muito extenso.")
    for k,v in dados.items():
        campos=CAMPOS[contexto][k]
        valores = v.values() if isinstance(v,dict) else [v]
        if campos is not None and (not isinstance(v,dict) or set(v)-campos):
            raise serializers.ValidationError("Campos inválidos neste formulário.")
        if campos is None and not isinstance(v,str):
            raise serializers.ValidationError("Formato inválido.")
        if any(not isinstance(x,(str,int,type(None))) or isinstance(x,bool) or isinstance(x,str) and len(x)>4000 for x in valores):
            raise serializers.ValidationError("Valor inválido no rascunho.")
    if dados.get("tipoLancamento","saida") not in ("saida","rascunho"):
        raise serializers.ValidationError("Tipo de lançamento inválido.")
    return dados

class RascunhoView(NoStoreResponseMixin, APIView):
    permission_classes=(permissions.IsAuthenticated,)
    def permitido(self,request,contexto):
        if contexto not in CAMPOS or not pode(request.user,contexto,"cadastrar"):
            raise PermissionDenied()
    def get(self,request,contexto):
        self.permitido(request,contexto)
        obj=RascunhoFormulario.objects.filter(usuario=request.user,contexto=contexto).first()
        return Response({"dados":obj.dados if obj else None,"atualizado_em":obj.atualizado_em if obj else None})
    def put(self,request,contexto):
        self.permitido(request,contexto)
        dados=validar_dados(contexto,request.data.get("dados"))
        obj,_=RascunhoFormulario.objects.update_or_create(usuario=request.user,contexto=contexto,defaults={"dados":dados})
        return Response({"dados":obj.dados,"atualizado_em":obj.atualizado_em})
    def delete(self,request,contexto):
        self.permitido(request,contexto)
        RascunhoFormulario.objects.filter(usuario=request.user,contexto=contexto).delete()
        return Response(status=204)

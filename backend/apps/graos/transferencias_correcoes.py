"""Correções atômicas de transferências: preserva original, estorna as duas pernas e reaplica."""
import hashlib
import json
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from rest_framework import permissions, serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.accounts.access import pode
from apps.accounts.views import NoStoreResponseMixin
from .models import CorrecaoTransferenciaSaldo, MovimentacaoGraos, OrigemSaldoGraos, PosicaoSaldoGraos
from .serializers import TransferirSaldoFisicoSerializer
from .services import SaldoGraosError, estornar_movimentacao, transferir_saldo_fisico, _bloquear_cadpros_para_saldo, _bloquear_armazens


def canonico(valor):
    if isinstance(valor,dict):return {k:canonico(v) for k,v in valor.items()}
    if isinstance(valor,list):return [canonico(v) for v in valor]
    return str(getattr(valor,"pk",valor))


@transaction.atomic
def corrigir_transferencia(*,usuario,movimento,acao,motivo,chave,dados=None):
    if acao not in ("editar","excluir"):raise SaldoGraosError("Ação de correção inválida.")
    motivo=str(motivo or "").strip();chave=str(chave or "").strip()
    if not motivo or len(motivo)>500 or not chave or len(chave)>160:
        raise SaldoGraosError("Informe motivo de até 500 caracteres e chave de idempotência válida.")
    payload={"movimento":movimento.pk,"acao":acao,"motivo":motivo,"dados":dados or {}}
    hash_req=hashlib.sha256(json.dumps(canonico(payload),sort_keys=True).encode()).hexdigest()
    if movimento.operacao!=MovimentacaoGraos.Operacao.TRANSFERENCIA_SAIDA:
        raise SaldoGraosError("Selecione o movimento de saída de uma transferência.")
    OrigemSaldoGraos.objects.select_for_update().get(pk=movimento.origem_id)
    existente=CorrecaoTransferenciaSaldo.objects.filter(chave_idempotencia=chave).first()
    if existente:
        if existente.hash_requisicao!=hash_req:raise SaldoGraosError("Esta chave já foi utilizada com outros dados.")
        return existente,True
    if CorrecaoTransferenciaSaldo.objects.filter(origem_original_id=movimento.origem_id).exists():
        raise SaldoGraosError("Esta transferência já foi editada ou excluída. Atualize o histórico.")
    pernas=list(MovimentacaoGraos.objects.select_related("posicao").filter(origem_id=movimento.origem_id,operacao__in=("transferencia_saida","transferencia_entrada")))
    if len(pernas)!=2:raise SaldoGraosError("A transferência não possui débito e crédito íntegros.")
    cadpros={p.posicao.cad_pro_id for p in pernas};armazens={p.posicao.armazem_id for p in pernas}
    for lado in ("origem","destino"):
        lote=(dados or {}).get(f"lote_{lado}")
        if lote:cadpros.add(lote.cad_pro_id);armazens.add(lote.armazem_id)
    if (dados or {}).get("cad_pro_destino"):cadpros.add(dados["cad_pro_destino"].pk)
    _bloquear_cadpros_para_saldo(cadpros);_bloquear_armazens(armazens)
    token=hashlib.sha256(chave.encode()).hexdigest()
    # Negativo somente transitório dentro da transação de edição; validar todas as posições no final.
    estornar_movimentacao(usuario=usuario,movimentacao=movimento,chave_idempotencia=f"transferencia-correcao:{token}:estorno",observacoes=motivo,metadados={"transferencia_original":movimento.origem_id,"acao":acao},permitir_saldo_negativo_transitorio=acao=="editar")
    origem_nova=None
    posicoes={p.posicao_id for p in pernas}
    if acao=="editar":
        if not dados:raise SaldoGraosError("Informe os novos dados da transferência.")
        dados=dados.copy();dados["chave_idempotencia"]=f"transferencia-correcao:{token}:nova"
        resultado=transferir_saldo_fisico(usuario=usuario,**dados,metadados={"transferencia_original":movimento.origem_id,"motivo_correcao":motivo})
        origem_nova=resultado.origem
        origem_nova=getattr(origem_nova,"id",origem_nova)
        posicoes.update(m.posicao_id for m in resultado.movimentacoes)
    for p in PosicaoSaldoGraos.objects.filter(pk__in=posicoes):
        if p.saldo_fisico_kg<0 or p.saldo_disponivel_kg<0:
            raise SaldoGraosError("A correção deixaria saldo insuficiente em uma posição. Reveja vendas, reservas e transferências posteriores antes de corrigir.")
    registro=CorrecaoTransferenciaSaldo.objects.create(origem_original_id=movimento.origem_id,origem_nova_id=origem_nova,acao=acao,motivo=motivo,chave_idempotencia=chave,hash_requisicao=hash_req,criado_por=usuario)
    return registro,False


class CorrecaoTransferenciaView(NoStoreResponseMixin,APIView):
    permission_classes=(permissions.IsAuthenticated,)
    def alterar(self,request,pk,acao):
        if not pode(request.user,"transferencias",acao):raise PermissionDenied()
        movimento=get_object_or_404(MovimentacaoGraos.objects.select_related("origem"),pk=pk,operacao="transferencia_saida")
        motivo=serializers.CharField(max_length=500).run_validation(request.data.get("motivo"))
        chave=serializers.CharField(max_length=160).run_validation(request.data.get("chave_idempotencia"))
        dados=None
        if acao=="editar":
            entrada=TransferirSaldoFisicoSerializer(data=request.data);entrada.is_valid(raise_exception=True);dados=entrada.validated_data
            dados.pop("chave_idempotencia",None);dados.pop("metadados",None)
        try:
            registro,idempotente=corrigir_transferencia(usuario=request.user,movimento=movimento,acao=acao,motivo=motivo,chave=chave,dados=dados)
        except IntegrityError:
            return Response({"detail":"Esta chave já foi usada em outra correção. Atualize o histórico.","codigo":"correcao_concorrente"},status=409)
        except SaldoGraosError as exc:
            return Response({"detail":str(exc),"codigo":exc.codigo},status=409)
        return Response({"id":registro.pk,"acao":registro.acao,"origem_original":registro.origem_original_id,"origem_nova":registro.origem_nova_id,"motivo":registro.motivo,"idempotente":idempotente})
    def patch(self,request,pk):return self.alterar(request,pk,"editar")
    def delete(self,request,pk):return self.alterar(request,pk,"excluir")

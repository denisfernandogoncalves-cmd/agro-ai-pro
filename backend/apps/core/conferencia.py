"""Conferência somente leitura; nunca invoca a reconciliação que altera saldos."""
from decimal import Decimal
from django.db.models import Sum, Q
from django.shortcuts import get_object_or_404
from rest_framework import permissions, serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.accounts.access import pode
from apps.accounts.views import NoStoreResponseMixin
from apps.graos.models import PosicaoSaldoGraos, MovimentacaoGraos

ZERO = Decimal("0")

class ConferenciaView(NoStoreResponseMixin, APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, pk):
        if not pode(request.user, "producao-saldos"):
            raise PermissionDenied()
        posicao = get_object_or_404(PosicaoSaldoGraos.objects.select_related("propriedade", "cad_pro", "armazem"), pk=pk)
        try:
            pagina = int(request.query_params.get("pagina", 1))
            if pagina < 1 or pagina > 1000000: raise ValueError()
        except (TypeError, ValueError):
            raise serializers.ValidationError({"pagina": "Página inválida."})
        qs = MovimentacaoGraos.objects.filter(posicao=posicao)
        totais = qs.aggregate(fisico=Sum("delta_fisico_kg"), comprometido=Sum("delta_comprometido_kg"), entradas=Sum("delta_fisico_kg", filter=Q(delta_fisico_kg__gt=0)), saidas=Sum("delta_fisico_kg", filter=Q(delta_fisico_kg__lt=0)), ajustes=Sum("delta_fisico_kg", filter=Q(operacao="ajuste")))
        totais = {k: v or ZERO for k,v in totais.items()}
        inicio = (pagina - 1) * 25
        movimentos = list(qs.select_related("movimento_estorno", "carga_colhida", "rateio_carga_colhida", "entrega_venda", "devolucao_venda", "origem", "reserva__origem").order_by("data_movimento", "id")[inicio:inicio + 25])
        # Baseline da página inclui todos os movimentos anteriores na mesma ordenação.
        anteriores = qs.filter(Q(data_movimento__lt=movimentos[0].data_movimento) | Q(data_movimento=movimentos[0].data_movimento, id__lt=movimentos[0].id)) if movimentos else qs.none()
        baseline = anteriores.aggregate(f=Sum("delta_fisico_kg"), c=Sum("delta_comprometido_kg"))
        fisico, comprometido = baseline["f"] or ZERO, baseline["c"] or ZERO
        itens=[]
        for m in movimentos:
            fisico += m.delta_fisico_kg; comprometido += m.delta_comprometido_kg
            correcao = ""
            if hasattr(m,"carga_colhida") or hasattr(m,"rateio_carga_colhida"):
                correcao = "Corrija pela carga colhida."
            elif hasattr(m,"entrega_venda") or hasattr(m,"devolucao_venda") or m.origem.metadados.get("venda_id") or (m.reserva_id and m.reserva.origem.metadados.get("venda_id")):
                correcao = "Corrija pela venda."
            elif m.operacao in ("transferencia_saida", "transferencia_entrada"):
                correcao = "A transferência exige estorno das duas posições pelo fluxo de transferências."
            itens.append({"orientacao_correcao":correcao,"id":m.id,"data":m.data_movimento,"operacao":m.operacao,"quantidade_kg":str(m.quantidade_kg),"delta_fisico_kg":str(m.delta_fisico_kg),"delta_comprometido_kg":str(m.delta_comprometido_kg),"saldo_acumulado_kg":str(fisico),"comprometido_acumulado_kg":str(comprometido),"referencia":m.referencia_externa,"motivo":m.observacoes,"estorno_de":m.estorno_de_id,"estornado":hasattr(m,"movimento_estorno")})
        return Response({"posicao":pk,"propriedade":posicao.propriedade.nome if posicao.propriedade_id else "Histórico sem propriedade","cad_pro":posicao.cad_pro.codigo,"armazem":posicao.armazem.nome,"versao":posicao.versao,"saldo_registrado_kg":str(posicao.saldo_fisico_kg),"comprometido_registrado_kg":str(posicao.saldo_comprometido_kg),"totais":{k:str(v) for k,v in totais.items()},"diferenca_fisico_kg":str(posicao.saldo_fisico_kg-totais["fisico"]),"diferenca_comprometido_kg":str(posicao.saldo_comprometido_kg-totais["comprometido"]),"pagina":pagina,"total_movimentos":qs.count(),"itens":itens})


class EstornoConferidoView(NoStoreResponseMixin, APIView):
    permission_classes = (permissions.IsAuthenticated,)
    def post(self, request, pk):
        if not pode(request.user, "producao-saldos", "excluir"):
            raise PermissionDenied()
        motivo = request.data.get("observacoes", "")
        if not isinstance(motivo,str) or not motivo.strip() or len(motivo)>2000:
            raise serializers.ValidationError({"observacoes":"Informe o motivo do estorno (até 2000 caracteres)."})
        from apps.graos.serializers import EstornoMovimentacaoSerializer
        from apps.graos.services import estornar_movimentacao
        from apps.graos.views import _executar_operacao
        dados=request.data.copy();dados["movimentacao"]=pk;dados["observacoes"]=motivo.strip()
        return _executar_operacao(request, EstornoMovimentacaoSerializer, estornar_movimentacao, dados=dados)


class SimularVendaSerializer(serializers.Serializer):
    from apps.vendas.serializers import NovaPosicaoVendaSerializer
    posicao = serializers.PrimaryKeyRelatedField(queryset=PosicaoSaldoGraos.objects.all(), required=False)
    nova_posicao = NovaPosicaoVendaSerializer(required=False)
    quantidade_kg = serializers.DecimalField(max_digits=16, decimal_places=3, min_value=Decimal("0.001"))
    tipo = serializers.ChoiceField(choices=("saida","rascunho"))
    def validate(self, attrs):
        if bool(attrs.get("posicao")) == bool(attrs.get("nova_posicao")):
            raise serializers.ValidationError("Informe uma posição existente ou uma nova origem.")
        return attrs

class SimularVendaView(NoStoreResponseMixin, APIView):
    permission_classes = (permissions.IsAuthenticated,)
    def post(self, request):
        if not pode(request.user,"vendas"):
            raise PermissionDenied()
        s=SimularVendaSerializer(data=request.data);s.is_valid(raise_exception=True);d=s.validated_data
        p=d.get("posicao")
        if not p:
            origem=d["nova_posicao"].copy();origem["classificacao_codigo"]=origem["classificacao_codigo"].strip().upper();origem["safra"]=origem["safra"].strip()
            p=PosicaoSaldoGraos.objects.filter(**origem).first()
        fisico=p.saldo_fisico_kg if p else ZERO;comprometido=p.saldo_comprometido_kg if p else ZERO
        posterior=fisico-d["quantidade_kg"] if d["tipo"]=="saida" else fisico
        return Response({"saldo_anterior_kg":str(fisico),"saldo_posterior_kg":str(posterior),"comprometido_kg":str(comprometido),"disponivel_posterior_kg":str(posterior-comprometido),"versao":p.versao if p else 0,"sem_lancamento":True})

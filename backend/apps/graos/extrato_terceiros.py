"""Extrato cronológico: estornos também entram no saldo acumulado."""
from decimal import Decimal
from django.db.models import Window, Sum, F
from django.db.models.functions import Lower, Trim
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.accounts.access import pode
from apps.accounts.views import NoStoreResponseMixin
from .models import MovimentoProducaoTerceiro


class FiltrosExtratoSerializer(serializers.Serializer):
    depositante = serializers.CharField(max_length=160, required=False, allow_blank=True)
    terceiro = serializers.IntegerField(min_value=1, required=False)
    entrada = serializers.IntegerField(min_value=1, required=False)
    cultura = serializers.CharField(max_length=50, required=False, allow_blank=True)
    safra = serializers.CharField(max_length=20, required=False, allow_blank=True)
    pagina = serializers.IntegerField(min_value=1, max_value=1000000, default=1)

    def validate(self,d):
        if not any(d.get(k) for k in ('terceiro','entrada','depositante')):
            raise serializers.ValidationError('Selecione o cadastro ou recebimento do terceiro.')
        return d


class ExtratoTerceirosView(NoStoreResponseMixin, APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        if not pode(request.user, "cargas", "consultar"):
            raise PermissionDenied()
        filtro = FiltrosExtratoSerializer(data=request.query_params)
        filtro.is_valid(raise_exception=True)
        dados = filtro.validated_data
        qs = MovimentoProducaoTerceiro.objects.all()
        if dados.get('terceiro'):
            qs=qs.filter(entrada__terceiro_id=dados['terceiro'])
        elif dados.get('entrada'):
            qs=qs.filter(entrada_id=dados['entrada'])
        else:
            ids=list(qs.filter(entrada__depositante__iexact=dados['depositante']).values_list('entrada__terceiro_id','entrada_id').distinct())
            identidades={('cad',t) if t else ('legado',e) for t,e in ids}
            if len(identidades)>1:
                raise serializers.ValidationError('Nome ambíguo. Selecione um cadastro ou recebimento específico.')
            qs=qs.filter(entrada__depositante__iexact=dados['depositante'])
        for campo in ("cultura", "safra"):
            if dados.get(campo):
                qs = qs.filter(**{f"entrada__{campo}__iexact": dados[campo]})
        # Partições evitam somar saldos de produtos/safras diferentes.
        qs = qs.annotate(acumulado=Window(Sum("delta_kg"), partition_by=[Lower(Trim("entrada__cultura")), Lower(Trim("entrada__safra"))], order_by=[F("data_movimento").asc(), F("id").asc()]))
        total = qs.count()
        inicio = (dados["pagina"] - 1) * 25
        itens = []
        for m in qs.select_related("entrada", "entrada__armazem", "criado_por", "estorno").order_by("data_movimento", "id")[inicio:inicio+25]:
            itens.append({"id": m.pk, "entrada": m.entrada_id, "data": m.data_movimento, "tipo": m.get_tipo_display(), "cultura": m.entrada.cultura, "safra": m.entrada.safra, "armazem": m.entrada.armazem.nome, "delta_kg": str(m.delta_kg), "saldo_acumulado_kg": str(m.acumulado or Decimal(0)), "saldo_recebimento_kg": str(m.saldo_posterior_kg), "documento": m.documento, "motivo": m.observacoes, "responsavel": m.criado_por.username, "estorno_de": m.estorno_de_id, "estornado": hasattr(m, "estorno")})
        return Response({"pagina": dados["pagina"], "total": total, "itens": itens})

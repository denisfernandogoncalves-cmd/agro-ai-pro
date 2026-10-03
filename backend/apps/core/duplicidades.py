from decimal import Decimal
from django.db.models import Q
from rest_framework import permissions, serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.accounts.access import pode
from apps.accounts.views import NoStoreResponseMixin
from apps.graos.models import CargaColhida, normalizar_placa
from apps.vendas.models import EntregaVendaGraos
from apps.financeiro.models import LancamentoFinanceiro


class ConsultaDuplicidade(serializers.Serializer):
    data = serializers.DateField()
    quantidade = serializers.DecimalField(max_digits=16, decimal_places=3, min_value=Decimal("0.001"))
    propriedade = serializers.IntegerField(required=False, min_value=1)
    cultura = serializers.CharField(required=False, allow_blank=True, max_length=50)
    safra = serializers.CharField(required=False, allow_blank=True, max_length=20)
    placa = serializers.CharField(required=False, allow_blank=True, max_length=12)
    nota_produtor = serializers.CharField(required=False, allow_blank=True, max_length=80)
    nota_empresa = serializers.CharField(required=False, allow_blank=True, max_length=80)
    destino = serializers.CharField(required=False, allow_blank=True, max_length=160)
    descricao = serializers.CharField(required=False, allow_blank=True, max_length=220)
    recebedor = serializers.CharField(required=False, allow_blank=True, max_length=160)
    excluir_id = serializers.IntegerField(required=False, min_value=1)


class DuplicidadesView(NoStoreResponseMixin, APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, entidade):
        modulo = {"carga":"cargas", "venda":"vendas", "financeiro":"financeiro"}.get(entidade)
        if not modulo:
            raise serializers.ValidationError("Tipo de lançamento inválido.")
        if not pode(request.user, modulo):
            raise PermissionDenied()
        serializer = ConsultaDuplicidade(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        if entidade == "carga":
            qs = CargaColhida.objects.filter(status="ativa", data_colheita=d["data"], peso_bruto_kg=d["quantidade"])
            for campo in ("cultura", "safra", "propriedade"):
                if d.get(campo):
                    qs = qs.filter(**{campo: d[campo]})
            if d.get("placa"):
                qs = qs.filter(placa=normalizar_placa(d["placa"]))
            if d.get("excluir_id"):
                qs = qs.exclude(pk=d["excluir_id"])
            itens = [{"id":i.pk,"referencia":f"Carga #{i.pk} · {i.propriedade.nome}"} for i in qs.select_related("propriedade").order_by("-id")[:5]]
        elif entidade == "venda":
            qs = EntregaVendaGraos.objects.filter(cancelado_em__isnull=True, venda__excluida_em__isnull=True)
            if d.get("destino"):
                qs = qs.filter(destino__iexact=d["destino"].strip())
            nota = Q(pk__in=[])
            if d.get("nota_produtor"):
                nota |= Q(nota_produtor__iexact=d["nota_produtor"].strip())
            if d.get("nota_empresa"):
                nota |= Q(nota_empresa__iexact=d["nota_empresa"].strip())
            coincidencia = Q(data_entrega=d["data"], quantidade_kg=d["quantidade"])
            if d.get("placa"):
                coincidencia &= Q(placa__iexact=normalizar_placa(d["placa"]))
            qs = qs.filter(nota | coincidencia)
            if d.get("cultura"):
                qs = qs.filter(venda__posicao__cultura=d["cultura"])
            itens = [{"id":i.venda_id,"referencia":f"Venda #{i.venda_id} · entrega #{i.pk} · {i.destino}"} for i in qs.order_by("-id")[:5]]
        else:
            qs = LancamentoFinanceiro.objects.filter(data_vencimento=d["data"], valor=d["quantidade"]).exclude(status="cancelado")
            if not d.get("descricao"):
                raise serializers.ValidationError("Informe a descrição para conferir o lançamento.")
            qs = qs.filter(descricao__iexact=d["descricao"].strip())
            if d.get("recebedor"):
                qs = qs.filter(recebedor_nome__iexact=d["recebedor"].strip())
            itens = [{"id":i.pk,"referencia":f"Lançamento #{i.pk} · {i.descricao}"} for i in qs.order_by("-id")[:5]]
        return Response({"total": qs.count(), "itens": itens, "aviso":"São possíveis duplicidades. Confira os documentos: lançamentos semelhantes podem ser legítimos."})

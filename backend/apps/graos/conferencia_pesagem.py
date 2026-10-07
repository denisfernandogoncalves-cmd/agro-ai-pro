"""Prévia sem movimentação e alertas informativos sobre pesagens comparáveis."""
from decimal import Decimal
from statistics import median

from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import get_object_or_404

from apps.accounts.access import pode
from apps.accounts.views import NoStoreResponseMixin
from .models import CargaColhida, EntradaProducaoTerceiro, MovimentoProducaoTerceiro, normalizar_placa
from .terceiros import CalculoSerializer, EntradaSerializer


class ContextoPesagemSerializer(serializers.Serializer):
    origem = serializers.ChoiceField(choices=("propria", "terceiro"))
    armazem = serializers.IntegerField(min_value=1)
    propriedade = serializers.IntegerField(min_value=1, required=False)
    terceiro = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    depositante = serializers.CharField(max_length=160, required=False)
    safra = serializers.CharField(max_length=20)
    placa = serializers.CharField(max_length=8, required=False, allow_blank=True, default="")
    excluir_id = serializers.IntegerField(min_value=1, required=False)
    data_entrada = serializers.DateField(required=False)
    data_colheita = serializers.DateField(required=False)

    def validate(self, dados):
        campo = "propriedade" if dados["origem"] == "propria" else "depositante"
        if campo not in dados and not dados.get("terceiro"):
            raise serializers.ValidationError({campo: "Informe o produtor para a conferência."})
        dados["placa"] = normalizar_placa(dados["placa"])
        return dados


def alertas_pesagem(contexto, calculo):
    filtros = {"armazem_id": contexto["armazem"], "safra": contexto["safra"], "cultura__iexact": calculo["cultura"]}
    if contexto["origem"] == "propria":
        historico = CargaColhida.objects.filter(**filtros, propriedade_id=contexto["propriedade"], status=CargaColhida.Status.ATIVA)
    else:
        canceladas = MovimentoProducaoTerceiro.objects.filter(tipo="entrada", estorno__isnull=False).values("entrada_id")
        identidade={"terceiro_id":contexto["terceiro"]} if contexto.get("terceiro") else {"depositante__iexact":contexto["depositante"],"terceiro__isnull":True}
        historico = EntradaProducaoTerceiro.objects.filter(**filtros, **identidade).exclude(pk__in=canceladas)
    if contexto["placa"]:
        historico = historico.filter(placa__iexact=contexto["placa"])
    if contexto.get("excluir_id"):
        historico = historico.exclude(pk=contexto["excluir_id"])
    amostra = list(historico.order_by("-criado_em", "-pk").values("tara_kg", "peso_bruto_kg")[:20])
    alertas = []
    for campo, limite, rotulo in (("tara_kg", Decimal("30"), "Tara"), ("peso_bruto_kg", Decimal("50"), "Bruto do produto")):
        valor = calculo.get(campo)
        if valor is None or (campo == "tara_kg" and not contexto["placa"]):
            continue
        valores = [item[campo] for item in amostra if item[campo] is not None and item[campo] > 0]
        if len(valores) < 5:
            continue
        referencia = median(valores)
        diferenca = abs(valor - referencia) * 100 / referencia
        if diferenca > limite:
            alertas.append({"campo": campo, "rotulo": rotulo, "mediana_kg": str(referencia), "valor_kg": str(valor), "desvio_percentual": str(diferenca.quantize(Decimal("0.1"))), "amostras": len(valores)})
    return alertas


class ConferenciaPesagemView(NoStoreResponseMixin, APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        if not pode(request.user, "cargas", "consultar"):
            raise PermissionDenied("Sem permissão para conferir pesagens.")
        contexto = ContextoPesagemSerializer(data=request.data)
        contexto.is_valid(raise_exception=True)
        entrada = None
        if contexto.validated_data["origem"] == "terceiro" and contexto.validated_data.get("excluir_id"):
            entrada = get_object_or_404(EntradaProducaoTerceiro, pk=contexto.validated_data["excluir_id"])
        # A edição preserva as regras da entrada; a conferência deve mostrar
        # exatamente o líquido que o serializer de gravação calculará.
        dados_entrada = request.data.copy()
        dados_entrada["placa"] = contexto.validated_data["placa"]
        calculo = EntradaSerializer(instance=entrada, data=dados_entrada) if entrada else CalculoSerializer(data=request.data)
        calculo.is_valid(raise_exception=True)
        campos = set(CalculoSerializer().fields) | {"peso_liquido_kg", "desconto_total_percentual", "desconto_total_kg", "regra_desconto_aplicada"}
        dados = {campo: valor for campo, valor in calculo.validated_data.items() if campo in campos}
        c = contexto.validated_data
        duplicados = []
        data = c.get("data_entrada" if c["origem"] == "terceiro" else "data_colheita")
        if data:
            filtros = {"cultura__iexact": dados["cultura"], "safra__iexact": c["safra"], "placa__iexact": c["placa"], "peso_bruto_kg": dados["peso_bruto_kg"]}
            if c["origem"] == "terceiro":
                canceladas = MovimentoProducaoTerceiro.objects.filter(tipo="entrada", estorno__isnull=False).values("entrada_id")
                identidade={"terceiro_id":c["terceiro"]} if c.get("terceiro") else {"depositante__iexact":c["depositante"],"terceiro__isnull":True}
                qs = EntradaProducaoTerceiro.objects.filter(**filtros, **identidade, data_entrada=data).exclude(pk__in=canceladas)
            else:
                qs = CargaColhida.objects.filter(**filtros, propriedade_id=c["propriedade"], data_colheita=data, status=CargaColhida.Status.ATIVA)
            if c.get("excluir_id"):
                qs = qs.exclude(pk=c["excluir_id"])
            duplicados = list(qs.order_by("id").values_list("id", flat=True)[:10])
        return Response({**dados, "alertas": alertas_pesagem(c, dados), "duplicados": duplicados})

"""Recebimentos e retiradas independentes da produção própria."""
import hashlib
import json
from decimal import Decimal

from django.db import IntegrityError, transaction
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import get_object_or_404

from apps.accounts.access import pode
from apps.accounts.views import NoStoreResponseMixin
from .models import ArmazemGraos, EntradaProducaoTerceiro, MovimentoProducaoTerceiro, normalizar_placa


from .cargas_services import calcular_peso_liquido, CargaColhidaError


class CalculoSerializer(serializers.Serializer):
    cultura = serializers.CharField()
    peso_bruto_kg = serializers.DecimalField(max_digits=16, decimal_places=3, min_value=Decimal("0.001"))
    umidade_percentual = serializers.DecimalField(max_digits=6, decimal_places=3, min_value=0, max_value=100)
    impureza_percentual = serializers.DecimalField(max_digits=6, decimal_places=3, min_value=0, max_value=100)
    defeitos_percentual = serializers.DecimalField(max_digits=6, decimal_places=3, min_value=0, max_value=100)
    ph = serializers.DecimalField(max_digits=6, decimal_places=3, min_value=0, max_value=100, required=False, allow_null=True)
    tolerancia_impureza_percentual = serializers.DecimalField(max_digits=6, decimal_places=3, min_value=0, max_value=100, required=False)
    desconto_impureza_por_ponto = serializers.DecimalField(max_digits=6, decimal_places=3, min_value=0, max_value=100, required=False)
    tolerancia_defeitos_percentual = serializers.DecimalField(max_digits=6, decimal_places=3, min_value=0, max_value=100, required=False)
    desconto_defeitos_por_ponto = serializers.DecimalField(max_digits=6, decimal_places=3, min_value=0, max_value=100, required=False)
    ph_minimo = serializers.DecimalField(max_digits=6, decimal_places=3, min_value=0, max_value=100, required=False)
    desconto_ph_por_ponto = serializers.DecimalField(max_digits=6, decimal_places=3, min_value=0, max_value=100, required=False)

    def validate(self, dados):
        try:
            percentual, desconto, liquido, sacas, regra = calcular_peso_liquido(**dados)
        except CargaColhidaError as exc:
            raise serializers.ValidationError(str(exc)) from exc
        return {**dados, "peso_liquido_kg": liquido, "desconto_total_percentual": percentual, "desconto_total_kg": desconto, "regra_desconto_aplicada": regra}


class EntradaSerializer(serializers.ModelSerializer):
    armazem_nome = serializers.CharField(source="armazem.nome", read_only=True)
    movimentos = serializers.SerializerMethodField()

    class Meta:
        model = EntradaProducaoTerceiro
        fields = ("id", "depositante", "propriedade_origem", "cad_pro", "cultura", "safra", "armazem", "armazem_nome", "peso_liquido_kg", "saldo_kg", "data_entrada", "placa", "motorista", "documento", "observacoes", "criado_em", "movimentos", "peso_bruto_kg", "umidade_percentual", "impureza_percentual", "defeitos_percentual", "ph", "desconto_total_percentual", "desconto_total_kg", "regra_desconto_aplicada")
        read_only_fields = ("saldo_kg", "criado_em", "peso_liquido_kg", "desconto_total_percentual", "desconto_total_kg", "regra_desconto_aplicada", "propriedade_origem", "cad_pro")

    def validate(self, dados):
        calculo = CalculoSerializer(data={k: self.initial_data[k] for k in CalculoSerializer().fields if k in self.initial_data})
        calculo.is_valid(raise_exception=True)
        calculados = calculo.validated_data
        campos = {f.name for f in EntradaProducaoTerceiro._meta.fields}
        return {**dados, **{k: v for k, v in calculados.items() if k in campos}}

    def validate_peso_liquido_kg(self, valor):
        if valor <= 0:
            raise serializers.ValidationError("Informe peso líquido maior que zero.")
        return valor

    def validate_placa(self, valor):
        return normalizar_placa(valor)

    def get_movimentos(self, obj):
        return MovimentoSerializer(obj.movimentos.all(), many=True).data


class MovimentoSerializer(serializers.ModelSerializer):
    criado_por_nome = serializers.CharField(source="criado_por.username", read_only=True)
    estornado = serializers.SerializerMethodField()

    class Meta:
        model = MovimentoProducaoTerceiro
        exclude = ("hash_requisicao", "chave_idempotencia")

    def get_estornado(self, obj):
        return hasattr(obj, "estorno")


class SaidaSerializer(serializers.Serializer):
    quantidade_kg = serializers.DecimalField(max_digits=16, decimal_places=3, min_value=Decimal("0.001"))
    data_movimento = serializers.DateField()
    destino = serializers.CharField(max_length=160)
    documento = serializers.CharField(max_length=120, required=False, allow_blank=True)
    placa = serializers.CharField(max_length=7, required=False, allow_blank=True)
    motorista = serializers.CharField(max_length=120, required=False, allow_blank=True)
    observacoes = serializers.CharField(max_length=4000, required=False, allow_blank=True)


class EstornoSerializer(serializers.Serializer):
    motivo = serializers.CharField(max_length=500)
    data_movimento = serializers.DateField()


def executar_terceiro(*, usuario, tipo, dados, chave, pk=None):
    if not chave or len(chave) > 160:
        raise serializers.ValidationError("Informe a chave de reenvio do lançamento.")
    # Valores normalizados identificam a intenção; uma chave não pode mudar dados/usuário.
    resumo = {k: v.pk if hasattr(v, "pk") else str(v) for k, v in dados.items()}
    digest = hashlib.sha256(json.dumps([tipo, pk, resumo], sort_keys=True).encode()).hexdigest()

    def repetido():
        movimento = MovimentoProducaoTerceiro.objects.filter(chave_idempotencia=chave).first()
        if movimento and (movimento.hash_requisicao != digest or movimento.criado_por_id != usuario.pk):
            raise serializers.ValidationError("Esta chave já foi usada em outro lançamento.")
        return movimento

    anterior = repetido()
    if anterior:
        return anterior.entrada, True
    if tipo == "entrada":
        armazem_id = dados["armazem"].pk
    elif tipo == "saida":
        armazem_id = get_object_or_404(EntradaProducaoTerceiro, pk=pk).armazem_id
    else:
        armazem_id = get_object_or_404(MovimentoProducaoTerceiro, pk=pk).entrada.armazem_id
    try:
        with transaction.atomic():
            armazem = ArmazemGraos.objects.select_for_update().get(pk=armazem_id)
            anterior = repetido()
            if anterior:
                return anterior.entrada, True
            if not armazem.ativo:
                raise serializers.ValidationError("O armazém está inativo.")
            if tipo == "entrada":
                entrada = EntradaProducaoTerceiro(**dados, criado_por=usuario, saldo_kg=0)
                delta = dados["peso_liquido_kg"]
                movimento_dados = {"data_movimento": entrada.data_entrada, "documento": entrada.documento, "placa": entrada.placa, "motorista": entrada.motorista, "observacoes": entrada.observacoes}
            else:
                original = get_object_or_404(MovimentoProducaoTerceiro, pk=pk) if tipo == "estorno" else None
                entrada_id = original.entrada_id if original else pk
                entrada = EntradaProducaoTerceiro.objects.select_for_update().get(pk=entrada_id)
                if tipo == "saida":
                    if entrada.movimentos.filter(tipo="entrada", estorno__isnull=False).exists():
                        raise serializers.ValidationError("Esta entrada foi estornada.")
                    delta = -dados["quantidade_kg"]
                    movimento_dados = {k: v for k, v in dados.items() if k != "quantidade_kg"}
                else:
                    if original.tipo == "estorno" or hasattr(original, "estorno"):
                        raise serializers.ValidationError("Este movimento já foi estornado ou é um estorno.")
                    delta = -original.delta_kg
                    movimento_dados = {"data_movimento": dados["data_movimento"], "observacoes": dados["motivo"], "estorno_de": original}
            saldo_anterior = entrada.saldo_kg
            saldo_novo = saldo_anterior + delta
            if saldo_novo < 0 or saldo_novo > entrada.peso_liquido_kg:
                raise serializers.ValidationError("Saldo de terceiros insuficiente. Confira as retiradas e seus estornos.")
            if delta > 0:
                from .services import _ocupacao_armazem_bloqueada
                if _ocupacao_armazem_bloqueada(armazem.pk) + delta > armazem.capacidade_kg:
                    raise serializers.ValidationError("Capacidade do armazém insuficiente para esta entrada.")
            entrada.saldo_kg = saldo_novo
            entrada.save()
            MovimentoProducaoTerceiro.objects.create(entrada=entrada, tipo=tipo, quantidade_kg=abs(delta), delta_kg=delta, saldo_anterior_kg=saldo_anterior, saldo_posterior_kg=saldo_novo, chave_idempotencia=chave, hash_requisicao=digest, criado_por=usuario, **movimento_dados)
            return entrada, False
    except IntegrityError:
        anterior = repetido()
        if anterior:
            return anterior.entrada, True
        raise serializers.ValidationError("Não foi possível registrar. Atualize e confira o lançamento.")


class TerceirosView(NoStoreResponseMixin, APIView):
    permission_classes = (IsAuthenticated,)
    tipo = "entrada"

    def verificar(self, request, acao):
        if not pode(request.user, "cargas", acao):
            raise PermissionDenied("Sem permissão para produção de terceiros.")

    def get(self, request, pk=None):
        self.verificar(request, "consultar")
        if self.tipo != "entrada":
            return Response(status=405)
        itens = EntradaProducaoTerceiro.objects.select_related("armazem").prefetch_related("movimentos__criado_por", "movimentos__estorno")
        return Response(EntradaSerializer(itens, many=True).data)

    def post(self, request, pk=None):
        if self.tipo == "previa":
            self.verificar(request, "consultar")
            calculo = CalculoSerializer(data=request.data)
            calculo.is_valid(raise_exception=True)
            return Response(calculo.validated_data)
        self.verificar(request, "excluir" if self.tipo == "estorno" else "cadastrar")
        classe = {"entrada": EntradaSerializer, "saida": SaidaSerializer, "estorno": EstornoSerializer}[self.tipo]
        serializer = classe(data=request.data)
        serializer.is_valid(raise_exception=True)
        entrada, repetida = executar_terceiro(usuario=request.user, tipo=self.tipo, dados=serializer.validated_data, chave=request.headers.get("Idempotency-Key", ""), pk=pk)
        return Response(EntradaSerializer(entrada).data, status=200 if repetida else 201)

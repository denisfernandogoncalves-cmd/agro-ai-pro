"""Contagem física auditável: nenhuma movimentação ou correção automática."""
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.accounts.access import pode
from apps.accounts.views import NoStoreResponseMixin
from .models import ArmazemGraos, PosicaoSaldoGraos, EntradaProducaoTerceiro, ConferenciaEstoque


class ContagemSerializer(serializers.Serializer):
    armazem = serializers.PrimaryKeyRelatedField(queryset=ArmazemGraos.objects.all())
    cultura = serializers.ChoiceField(choices=("Soja", "Milho", "Trigo"))
    safra = serializers.CharField(max_length=20)
    data_contagem = serializers.DateField()
    contado_kg = serializers.DecimalField(max_digits=16, decimal_places=3, min_value=0)
    justificativa = serializers.CharField(max_length=2000)
    chave_idempotencia = serializers.UUIDField()

    def validate_data_contagem(self, valor):
        if valor > timezone.localdate():
            raise serializers.ValidationError("A contagem não pode ter data futura.")
        return valor


def representar(c):
    return {"id": c.pk, "armazem": c.armazem_id, "armazem_nome": c.armazem.nome, "cultura": c.cultura, "safra": c.safra, "data_contagem": c.data_contagem, "contado_kg": str(c.contado_kg), "saldo_proprio_kg": str(c.saldo_proprio_kg), "saldo_terceiros_kg": str(c.saldo_terceiros_kg), "saldo_registrado_kg": str(c.saldo_proprio_kg+c.saldo_terceiros_kg), "diferenca_kg": str(c.contado_kg-c.saldo_proprio_kg-c.saldo_terceiros_kg), "justificativa": c.justificativa, "responsavel": c.criado_por.username, "registrado_em": c.criado_em}


class ConferenciaEstoqueView(NoStoreResponseMixin, APIView):
    permission_classes = (IsAuthenticated,)
    previa = False

    def permitido(self, user, acao):
        if not any(pode(user, modulo, acao) for modulo in ("cargas", "producao-saldos")):
            raise PermissionDenied()

    def get(self, request):
        self.permitido(request.user, "consultar")
        if self.previa:
            s = ContagemSerializer(data={**request.query_params.dict(), "data_contagem": timezone.localdate(), "justificativa": "Prévia", "chave_idempotencia": "00000000-0000-0000-0000-000000000001"})
            s.is_valid(raise_exception=True)
            d = s.validated_data
            proprio, terceiros = saldo_estoque(d)
            return Response({"saldo_proprio_kg": str(proprio), "saldo_terceiros_kg": str(terceiros), "saldo_registrado_kg": str(proprio+terceiros), "diferenca_kg": str(d["contado_kg"]-proprio-terceiros)})
        return Response([representar(c) for c in ConferenciaEstoque.objects.select_related("armazem", "criado_por").order_by("-criado_em", "-id")[:50]])

    def post(self, request):
        self.permitido(request.user, "cadastrar")
        s = ContagemSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        with transaction.atomic():
            # A mesma trava de armazém usada pelas operações de estoque.
            ArmazemGraos.objects.select_for_update().get(pk=d["armazem"].pk)
            anterior = ConferenciaEstoque.objects.filter(chave_idempotencia=d["chave_idempotencia"]).first()
            if anterior:
                if anterior.criado_por_id != request.user.pk or any(getattr(anterior, campo) != d[campo] for campo in d):
                    raise serializers.ValidationError("Esta chave já foi usada para outra contagem.")
                return Response(representar(anterior))
            proprio, terceiros = saldo_estoque(d)
            c = ConferenciaEstoque.objects.create(**d, saldo_proprio_kg=proprio, saldo_terceiros_kg=terceiros, criado_por=request.user)
            diferenca=c.contado_kg-proprio-terceiros
            if diferenca:
                from .pendencias import registrar_pendencia
                registrar_pendencia(request.user,f'contagem:{c.pk}','estoque',f'Conferir diferença física #{c.pk}',{'contagem':c.pk,'armazem':c.armazem.nome,'cultura':c.cultura,'safra':c.safra,'diferenca_kg':str(diferenca)})
        return Response(representar(c), status=201)


def saldo_estoque(dados):
    filtros = {"armazem": dados["armazem"], "cultura__iexact": dados["cultura"], "safra__iexact": dados["safra"]}
    proprio = PosicaoSaldoGraos.objects.filter(**filtros).aggregate(v=Sum("saldo_fisico_kg"))["v"] or Decimal(0)
    terceiros = EntradaProducaoTerceiro.objects.filter(**filtros).aggregate(v=Sum("saldo_kg"))["v"] or Decimal(0)
    return proprio, terceiros

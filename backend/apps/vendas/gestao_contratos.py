from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum, Q
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.access import pode
from apps.cadpro.models import CADPro
from apps.core.models import RegistroAlteracao
from apps.graos.models import PosicaoSaldoGraos
from .models import ContratoComercial, VendaGraos, EntregaVendaGraos

ZERO = Decimal("0")

def vendas_validas(contrato):
    return VendaGraos.objects.filter(contrato=contrato, excluida_em__isnull=True)

def entregue(contrato, cad=None):
    qs = vendas_validas(contrato)
    if cad is not None:
        qs = qs.filter(posicao__cad_pro_id=cad)
    return qs.aggregate(total=Sum("quantidade_entregue_kg"))["total"] or ZERO

class CotaSerializer(serializers.Serializer):
    cad_pro = serializers.PrimaryKeyRelatedField(queryset=CADPro.objects.filter(ativo=True))
    quantidade_kg = serializers.DecimalField(max_digits=16, decimal_places=3, min_value=Decimal("0.001"))

class AgendaSerializer(CotaSerializer):
    data = serializers.DateField()


def validar_configuracao(attrs, instance):
    total = attrs.get("quantidade_kg", instance.quantidade_kg if instance else None)
    cotas = attrs.get("cotas_cadpro", instance.cotas_cadpro if instance else [])
    agendas = attrs.get("calendario_entregas", instance.calendario_entregas if instance else [])
    normalized = []
    for key, items, schema in (("cotas_cadpro", cotas, CotaSerializer), ("calendario_entregas", agendas, AgendaSerializer)):
        if not isinstance(items, list) or len(items) > 100:
            raise serializers.ValidationError({key: "Informe até 100 registros."})
        ser = schema(data=items, many=True)
        antigos = [row["cad_pro"] for row in getattr(instance,key,[]) ] if instance else []
        ser.child.fields["cad_pro"].queryset = CADPro.objects.filter(Q(ativo=True)|Q(pk__in=antigos))
        ser.is_valid(raise_exception=True)
        result = []
        for row in ser.validated_data:
            item = {"cad_pro": str(row["cad_pro"].pk), "quantidade_kg": str(row["quantidade_kg"])}
            if "data" in row:
                item["data"] = row["data"].isoformat()
            result.append(item)
        if key == "cotas_cadpro":
            normalized = result
            if len({row["cad_pro"] for row in result}) != len(result):
                raise serializers.ValidationError({key: "Cada CAD/PRO deve aparecer uma vez."})
        if key in attrs:
            attrs[key] = result
    distributed = sum((Decimal(row["quantidade_kg"]) for row in normalized), ZERO)
    if distributed and (total is None or distributed > total):
        raise serializers.ValidationError({"cotas_cadpro": "A distribuição excede o total contratado."})
    if instance:
        delivered = entregue(instance)
        if total is not None and total < delivered:
            raise serializers.ValidationError({"quantidade_kg": "O total não pode ficar abaixo do já entregue."})
        old = {r["cad_pro"]: Decimal(r["quantidade_kg"]) for r in instance.cotas_cadpro}
        new = {r["cad_pro"]: Decimal(r["quantidade_kg"]) for r in normalized}
        for cad in old:
            if new.get(cad, ZERO) < entregue(instance, cad):
                raise serializers.ValidationError({"cotas_cadpro": "Uma cota não pode ficar abaixo do já entregue."})
    return attrs


def resumo_contrato(contrato):
    delivered = entregue(contrato)
    total = contrato.quantidade_kg
    remaining = None if total is None else total - delivered
    quotas = []
    for row in contrato.cotas_cadpro:
        cad = CADPro.objects.get(pk=row["cad_pro"])
        amount = Decimal(row["quantidade_kg"])
        used = entregue(contrato, cad.pk)
        balances = PosicaoSaldoGraos.objects.filter(cad_pro=cad, cultura__iexact=contrato.produto).aggregate(fisico=Sum("saldo_fisico_kg"), comprometido=Sum("saldo_comprometido_kg"))
        physical = balances["fisico"] or ZERO
        committed = balances["comprometido"] or ZERO
        available = physical - committed
        reservada = vendas_validas(contrato).filter(posicao__cad_pro=cad,posicao__cultura__iexact=contrato.produto).aggregate(total=Sum("reserva__saldo_reservado_kg"))["total"] or ZERO
        cobertura = max(ZERO,available) + reservada
        quotas.append({"cad_pro": str(cad.pk), "codigo": cad.codigo, "quantidade_kg": str(amount), "entregue_kg": str(used), "restante_kg": str(amount-used), "fisico_kg": str(physical), "comprometido_kg": str(committed), "disponivel_kg": str(available), "falta_sem_reserva_kg": str(max(ZERO, amount-used-max(ZERO,available))), "reservado_proprio_contrato_kg":str(reservada), "comprometido_outros_kg":str(max(ZERO,committed-reservada)), "cobertura_kg":str(cobertura), "falta_com_reserva_propria_kg":str(max(ZERO,amount-used-cobertura))})
    distributed = sum((Decimal(row["quantidade_kg"]) for row in contrato.cotas_cadpro), ZERO)
    since = timezone.localdate() - timedelta(days=29)
    qs = EntregaVendaGraos.objects.filter(venda__in=vendas_validas(contrato), cancelado_em__isnull=True, data_entrega__gte=since, data_entrega__lte=timezone.localdate())
    recent = qs.aggregate(total=Sum("quantidade_kg"))["total"] or ZERO
    history = RegistroAlteracao.objects.filter(entidade="ContratoComercial", registro_id=str(contrato.pk)).values("usuario_nome","acao","alteracoes","criado_em")[:25]
    return {"total_kg": None if total is None else str(total), "entregue_kg": str(delivered), "restante_kg": None if remaining is None else str(remaining), "distribuido_kg": str(distributed), "nao_distribuido_kg": None if total is None else str(total-distributed), "alerta": remaining is not None and contrato.alerta_restante_kg is not None and remaining <= contrato.alerta_restante_kg, "cotas": quotas, "historico": list(history), "ritmo": {"periodo_inicio": since.isoformat(), "dias":30, "entregue_kg":str(recent)}, "aviso_cobertura": "Disponível compartilhado entre contratos, culturas conforme cadastro, todas as safras/armazéns. Não é reserva exclusiva. Reservas deste contrato são discriminadas separadamente; reservas de outros contratos não cobrem esta cota."}


class GestaoContratoMixin:
    def update(self, request, *args, **kwargs):
        with transaction.atomic():
            self.instance = ContratoComercial.objects.select_for_update().get(pk=self.get_object().pk)
            if str(request.data.get("versao", "")) != str(self.instance.versao):
                return Response({"detail":"O contrato mudou. Recarregue antes de salvar."},status=status.HTTP_409_CONFLICT)
            reason = str(request.data.get("justificativa", "")).strip()
            if not reason or len(reason)>2000:
                return Response({"justificativa":"Informe uma justificativa de até 2.000 caracteres."},status=400)
            serializer=self.get_serializer(self.instance,data=request.data,partial=kwargs.get("partial",False))
            serializer.is_valid(raise_exception=True)
            before=dict(self.get_serializer(self.instance).data)
            serializer.save(versao=self.instance.versao+1)
            RegistroAlteracao.objects.create(usuario=request.user,usuario_nome=request.user.get_username(),modulo="cadastros-agricolas",entidade="ContratoComercial",registro_id=str(self.instance.pk),acao="editar",alteracoes={"antes":before,"depois":dict(serializer.data),"justificativa":reason})
            return Response(serializer.data)

    @action(detail=True,methods=["get"])
    def acompanhamento(self,request,pk=None):
        result = resumo_contrato(self.get_object())
        if not pode(request.user, "producao-saldos", "consultar"):
            for row in result["cotas"]:
                for key in ("fisico_kg", "comprometido_kg", "disponivel_kg", "falta_sem_reserva_kg", "reservado_proprio_contrato_kg", "comprometido_outros_kg", "cobertura_kg", "falta_com_reserva_propria_kg"):
                    row[key] = None
        return Response(result)


def validar_entrega_contrato(venda, quantidade):
    if not venda.contrato_id:
        return
    contrato = ContratoComercial.objects.select_for_update().get(pk=venda.contrato_id)
    if not contrato.cotas_cadpro:
        return
    from .services import VendaGraosConflitoError
    if contrato.quantidade_kg is not None and entregue(contrato)+quantidade > contrato.quantidade_kg:
        raise VendaGraosConflitoError("A entrega excede o restante do contrato distribuído.")
    cota = next((r for r in contrato.cotas_cadpro if r["cad_pro"] == str(venda.posicao.cad_pro_id)),None)
    if cota and entregue(contrato,venda.posicao.cad_pro_id)+quantidade > Decimal(cota["quantidade_kg"]):
        raise VendaGraosConflitoError("A entrega excede o restante da cota CAD/PRO.")

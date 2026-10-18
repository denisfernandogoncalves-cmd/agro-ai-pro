from datetime import date
from django.db import IntegrityError, transaction
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from apps.accounts.access import pode, verificar_acesso
from apps.core.edicao_concorrente import EdicaoConcorrenteMixin
from apps.graos.models import CargaColhida, normalizar_placa
from apps.vendas.models import EntregaVendaGraos
from .models import FreteConferido, RemuneracaoMotorista
from .serializers import RemuneracaoSerializer
from apps.core.correcoes import CorrecaoHistoricoMixin, VersaoCorrecaoSerializer


def competencia_mes(mes):
    try:
        data = date.fromisoformat(str(mes) + "-01")
        if len(str(mes)) != 7:
            raise ValueError
        return data
    except (ValueError, TypeError):
        raise ValidationError({"mes": "Escolha um mês válido (AAAA-MM)."})


class FreteSerializer(VersaoCorrecaoSerializer, serializers.ModelSerializer):
    ja_contabilizado = serializers.BooleanField(required=True)

    class Meta:
        model = FreteConferido
        fields = "__all__"
        read_only_fields = ("atualizado_em",)

    def validate(self, attrs):
        carga = attrs.get("carga", getattr(self.instance, "carga", None))
        entrega = attrs.get("entrega", getattr(self.instance, "entrega", None))
        if bool(carga) == bool(entrega):
            raise ValidationError("Vincule exatamente uma carga ou uma entrega de venda.")
        user = self.context["request"].user
        if not pode(user, "cargas" if carga else "vendas", "consultar"):
            raise PermissionDenied("Sem acesso à origem deste frete.")
        origem = carga or entrega
        if (carga and carga.status != "ativa") or (entrega and entrega.cancelado_em):
            raise ValidationError("A origem está cancelada ou substituída.")
        rem = attrs.get("remuneracao", getattr(self.instance, "remuneracao", None))
        data = carga.data_colheita if carga else entrega.data_entrega
        if rem and rem.competencia != data.replace(day=1):
            raise ValidationError({"remuneracao": "Escolha a remuneração do mesmo mês da viagem."})
        placa = normalizar_placa(origem.placa)
        if rem and placa and rem.caminhao.placa != placa:
            raise ValidationError({"remuneracao": "A placa da remuneração deve corresponder à viagem."})
        if self.instance and (carga != self.instance.carga or entrega != self.instance.entrega):
            raise ValidationError("Não é possível trocar a origem de uma conferência existente.")
        return attrs


class FreteViewSet(CorrecaoHistoricoMixin, EdicaoConcorrenteMixin, viewsets.ModelViewSet):
    modulo_correcao = "transportes"
    campos_correcao = ("frete", "comissao", "ja_contabilizado", "observacoes")
    queryset = FreteConferido.objects.select_related("carga", "entrega", "remuneracao__caminhao")
    serializer_class = FreteSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def destroy(self, request, *args, **kwargs):
        return Response({"detail": "Use cancelar-registro com versão e motivo para preservar o original."}, status=405)

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        verificar_acesso(request.user, request.path, request.method)

    def create(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                return super().create(request, *args, **kwargs)
        except IntegrityError:
            return Response({"detail": "Esta viagem já foi conferida. Atualize a consulta antes de editar."}, status=409)

    @action(detail=False, methods=["get"])
    def cruzamento(self, request):
        mes = competencia_mes(request.query_params.get("mes"))
        placa = normalizar_placa(request.query_params.get("placa", ""))
        remun = RemuneracaoMotorista.objects.select_related("caminhao").filter(competencia=mes)
        if placa:
            remun = remun.filter(caminhao__placa=placa)
        linhas = []
        fontes = []
        if pode(request.user, "cargas", "consultar"):
            fontes.append(("carga", CargaColhida.objects.filter(status="ativa", data_colheita__year=mes.year, data_colheita__month=mes.month), "data_colheita", "peso_bruto_kg"))
        if pode(request.user, "vendas", "consultar"):
            fontes.append(("venda", EntregaVendaGraos.objects.filter(cancelado_em__isnull=True, data_entrega__year=mes.year, data_entrega__month=mes.month), "data_entrega", "quantidade_kg"))
        conferencias = self.get_queryset().filter(remuneracao__competencia=mes)
        mapa = {("carga" if c.carga_id else "venda", c.carga_id or c.entrega_id): c for c in conferencias}
        for tipo, qs, campo_data, campo_peso in fontes:
            # Placas antigas de vendas podem conter hífen ou espaços; normalizar antes de cruzar.
            for item in qs.only("id", "placa", "motorista", campo_data, campo_peso).order_by(campo_data, "id"):
                placa_origem = normalizar_placa(item.placa)
                if placa and placa_origem != placa:
                    continue
                conferencia = mapa.get((tipo, item.pk))
                linhas.append({"origem": tipo, "id": item.pk, "data": str(getattr(item, campo_data)),
                    "placa": placa_origem, "motorista": item.motorista, "peso_kg": str(getattr(item, campo_peso)),
                    "conferencia": FreteSerializer(conferencia).data if conferencia else None})
        return Response({"mes": str(mes)[:7], "remuneracoes": RemuneracaoSerializer(remun, many=True).data,
            "viagens": sorted(linhas, key=lambda i: (i["data"], i["placa"], i["origem"], i["id"]))})

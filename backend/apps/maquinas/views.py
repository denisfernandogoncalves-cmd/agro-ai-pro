from apps.core.edicao_concorrente import EdicaoConcorrenteMixin
from datetime import date
from django.db.models.deletion import ProtectedError
from rest_framework.exceptions import ValidationError
from apps.core.correcoes import CorrecaoHistoricoMixin
from decimal import Decimal
from django.utils.dateparse import parse_datetime

from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.core.pagination import PaginacaoOpcional
from apps.core.query_params import validar_filtros

from .models import AbastecimentoMaquina, Maquina, ManutencaoMaquina, UsoMaquina
from .serializers import (
    AbastecimentoMaquinaSerializer,
    MaquinaSerializer,
    ManutencaoMaquinaSerializer,
    UsoMaquinaSerializer,
)
from .services import concluir_manutencao


class MaquinaViewSet(EdicaoConcorrenteMixin, viewsets.ModelViewSet):
    queryset = Maquina.objects.select_related("propriedade")
    serializer_class = MaquinaSerializer
    pagination_class = PaginacaoOpcional
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ("identificacao", "marca", "modelo")
    ordering_fields = ("identificacao", "tipo", "status", "horimetro_atual")

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError:
            raise ValidationError("Máquina com histórico de uso, abastecimento ou manutenção não pode ser excluída. Marque-a como inativa.")

    def get_queryset(self):
        validar_filtros(self.request.query_params, ids=('propriedade', 'maquina', 'operacao'))
        queryset = super().get_queryset()
        for parametro in ("tipo", "status", "propriedade"):
            valor = self.request.query_params.get(parametro, "").strip()
            if valor:
                queryset = queryset.filter(**{parametro: valor})
        return queryset


def conferir_horimetro(instancia, request):
    maquina = Maquina.objects.select_for_update().get(pk=instancia.maquina_id)
    try:
        original = parse_datetime(str(request.data.get("versao_maquina_original", "")))
    except (ValueError, TypeError):
        original = None
    if original != maquina.atualizado_em:
        raise ValidationError("A máquina mudou desde a consulta. Atualize antes de confirmar o horímetro.")
    campo = MaquinaSerializer().fields["horimetro_atual"]
    if "horimetro_corrigido" not in request.data:
        raise ValidationError({"horimetro_corrigido": "Confirme o horímetro atual correto para reconciliar o histórico."})
    atual = campo.run_validation(request.data["horimetro_corrigido"])
    leituras = list(maquina.usos.values_list("horimetro_final", flat=True)) + list(maquina.abastecimentos.values_list("horimetro", flat=True)) + list(maquina.manutencoes.filter(status="concluida", horimetro_realizado__isnull=False).values_list("horimetro_realizado", flat=True))
    if leituras and atual < max(leituras):
        raise ValidationError({"horimetro_corrigido": "O horímetro atual não pode ser menor que as demais leituras registradas."})
    maquina.horimetro_atual = atual
    maquina.save(update_fields=["horimetro_atual", "atualizado_em"])


def corrigir_registro_maquina(instancia, dados, request):
    for nome, valor in dados.items():
        setattr(instancia, nome, valor)
    instancia.clean_fields()
    instancia.validate_unique()
    for campo in ("horimetro", "horimetro_inicial", "horimetro_final", "horimetro_previsto", "horimetro_realizado"):
        valor = getattr(instancia, campo, None)
        if valor is not None and valor < 0:
            raise ValidationError("Horímetros não podem ter valores negativos.")
    if isinstance(instancia, ManutencaoMaquina) and instancia.status == "concluida" and (instancia.data_conclusao is None or instancia.horimetro_realizado is None):
        raise ValidationError("Manutenção concluída exige data e horímetro realizado.")
    if isinstance(instancia, UsoMaquina) and (instancia.horimetro_inicial < 0 or instancia.horimetro_final <= instancia.horimetro_inicial):
        raise ValidationError("Horímetro final deve superar o inicial, sem leituras negativas.")
    if isinstance(instancia, UsoMaquina) and instancia.maquina.usos.exclude(pk=instancia.pk).filter(horimetro_inicial__lt=instancia.horimetro_final, horimetro_final__gt=instancia.horimetro_inicial).exists():
        raise ValidationError("O intervalo corrigido se sobrepõe a outro uso registrado da máquina.")
    instancia.save()
    conferir_horimetro(instancia, request)


class HistoricoMaquinaMixin(CorrecaoHistoricoMixin):
    modulo_correcao = "maquinas"

    def bloquear_dependencias(self, instancia):
        Maquina.objects.select_for_update().get(pk=instancia.maquina_id)

    def corrigir_historico(self, instancia, dados, request):
        corrigir_registro_maquina(instancia, dados, request)

    def cancelar_historico(self, instancia, request):
        maquina_id = instancia.maquina_id
        instancia.delete()
        instancia.maquina_id = maquina_id
        conferir_horimetro(instancia, request)
    pagination_class = PaginacaoOpcional
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    def update(self, request, *args, **kwargs):
        return Response(
            {"detail": "Registros históricos não podem ser editados."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def destroy(self, request, *args, **kwargs):
        return Response(
            {"detail": "Registros históricos não podem ser excluídos."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )


class UsoMaquinaViewSet(HistoricoMaquinaMixin, viewsets.ModelViewSet):
    campos_correcao = ("operador", "data", "horimetro_inicial", "horimetro_final", "observacoes")
    queryset = UsoMaquina.objects.select_related("maquina", "operacao")
    serializer_class = UsoMaquinaSerializer
    search_fields = ("maquina__identificacao", "operacao__descricao", "operador")
    ordering_fields = ("data", "horimetro_final")


class AbastecimentoMaquinaViewSet(HistoricoMaquinaMixin, viewsets.ModelViewSet):
    campos_correcao = ("data", "litros", "valor_total", "horimetro", "documento", "observacoes")
    queryset = AbastecimentoMaquina.objects.select_related("maquina")
    serializer_class = AbastecimentoMaquinaSerializer
    search_fields = ("maquina__identificacao", "documento")
    ordering_fields = ("data", "litros", "valor_total", "horimetro")


class ManutencaoMaquinaViewSet(CorrecaoHistoricoMixin, viewsets.ModelViewSet):
    modulo_correcao = "maquinas"
    campos_correcao = ("descricao", "data_prevista", "horimetro_previsto", "data_conclusao", "horimetro_realizado", "custo", "observacoes")

    def bloquear_dependencias(self, instancia):
        Maquina.objects.select_for_update().get(pk=instancia.maquina_id)

    def corrigir_historico(self, instancia, dados, request):
        corrigir_registro_maquina(instancia, dados, request)

    def cancelar_historico(self, instancia, request):
        if instancia.status == "cancelada":
            raise ValidationError("A manutenção já está cancelada.")
        instancia.status = "cancelada"
        instancia.custo = Decimal("0")
        instancia.save(update_fields=["status", "custo"])
        conferir_horimetro(instancia, request)

    queryset = ManutencaoMaquina.objects.select_related("maquina")
    serializer_class = ManutencaoMaquinaSerializer
    pagination_class = PaginacaoOpcional
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ("maquina__identificacao", "descricao", "observacoes")
    ordering_fields = ("data_prevista", "status", "custo")

    def update(self, request, *args, **kwargs):
        if self.get_object().status != ManutencaoMaquina.Status.AGENDADA:
            return Response(
                {"detail": "Manutenções encerradas não podem ser editadas."},
                status=status.HTTP_409_CONFLICT,
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if self.get_object().status != ManutencaoMaquina.Status.AGENDADA:
            return Response(
                {"detail": "Manutenções encerradas não podem ser excluídas."},
                status=status.HTTP_409_CONFLICT,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["post"])
    def concluir(self, request, pk=None):
        try:
            data_conclusao = request.data.get("data_conclusao")
            manutencao = concluir_manutencao(
                self.get_object(),
                data=date.fromisoformat(data_conclusao) if data_conclusao else None,
                horimetro=request.data.get("horimetro_realizado"),
                custo=request.data.get("custo"),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(self.get_serializer(manutencao).data)

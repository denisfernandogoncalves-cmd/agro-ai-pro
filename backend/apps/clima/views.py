from django.db.models import Avg, Max, Min, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.access import (
    PAPEIS_GESTAO,
    PAPEIS_LEITURA,
    PAPEIS_OPERACAO,
    exigir_acesso_propriedade,
    propriedades_visiveis,
)
from apps.core.viewsets import EscopoPropriedadeViewSetMixin

from .models import (
    AlertaClimatico,
    AtualizacaoClima,
    ConfiguracaoClima,
    PrevisaoClima,
    PrevisaoHoraria,
)
from .serializers import (
    AlertaClimaticoSerializer,
    AtualizacaoClimaSerializer,
    ConfiguracaoClimaSerializer,
    PrevisaoClimaSerializer,
    PrevisaoHorariaSerializer,
)
from .services import (
    AtualizacaoClimaEmAndamento,
    ServicoClimaError,
    atualizar_clima_propriedade,
)


def _propriedade_da_requisicao(request, origem="query"):
    dados = request.query_params if origem == "query" else request.data
    propriedade_id = dados.get("propriedade")
    if not propriedade_id:
        return None
    return get_object_or_404(
        propriedades_visiveis(request.user),
        pk=propriedade_id,
    )


class PrevisaoClimaViewSet(
    EscopoPropriedadeViewSetMixin,
    viewsets.ReadOnlyModelViewSet,
):
    queryset = PrevisaoClima.objects.select_related("propriedade").all()
    serializer_class = PrevisaoClimaSerializer
    property_filter = "propriedade_id"
    property_path = "propriedade"
    filter_backends = (filters.OrderingFilter,)
    ordering_fields = ("data", "temperatura_min", "temperatura_max", "chuva_mm")
    ordering = ("data",)

    def get_queryset(self):
        queryset = super().get_queryset()
        propriedade = self.request.query_params.get("propriedade", "").strip()
        data_inicio = self.request.query_params.get("data_inicio", "").strip()
        data_fim = self.request.query_params.get("data_fim", "").strip()
        if propriedade:
            queryset = (
                queryset.filter(propriedade_id=propriedade)
                if propriedade.isdecimal()
                else queryset.none()
            )
        if data_inicio:
            queryset = queryset.filter(data__gte=data_inicio)
        if data_fim:
            queryset = queryset.filter(data__lte=data_fim)
        return queryset

    @action(detail=False, methods=["post"])
    def atualizar(self, request):
        propriedade = _propriedade_da_requisicao(request, origem="data")
        if not propriedade:
            return Response(
                {"propriedade": ["Informe a propriedade."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        exigir_acesso_propriedade(
            request.user,
            propriedade,
            papeis=PAPEIS_OPERACAO,
        )
        try:
            resultado = atualizar_clima_propriedade(propriedade, force=True)
        except AtualizacaoClimaEmAndamento as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_409_CONFLICT,
            )
        except ServicoClimaError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        serializer = self.get_serializer(resultado["previsoes"], many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def status(self, request):
        propriedade = _propriedade_da_requisicao(request)
        if not propriedade:
            return Response(
                {"propriedade": ["Informe a propriedade."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        configuracao, _ = ConfiguracaoClima.objects.get_or_create(
            propriedade=propriedade
        )
        proxima_hora = (
            PrevisaoHoraria.objects.filter(
                propriedade=propriedade,
                data_hora__gte=timezone.now(),
            )
            .order_by("data_hora")
            .first()
        )
        return Response(
            {
                "configuracao": ConfiguracaoClimaSerializer(configuracao).data,
                "atual": configuracao.dados_atuais,
                "proxima_hora": (
                    PrevisaoHorariaSerializer(proxima_hora).data
                    if proxima_hora
                    else None
                ),
                "alertas_ativos": AlertaClimatico.objects.filter(
                    propriedade=propriedade,
                    ativo=True,
                ).count(),
            }
        )

    @action(detail=False, methods=["get"])
    def resumo(self, request):
        propriedade = _propriedade_da_requisicao(request)
        if not propriedade:
            return Response(
                {"propriedade": ["Informe a propriedade."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        queryset = self.get_queryset().filter(propriedade=propriedade)
        dados = queryset.aggregate(
            chuva_total=Sum("chuva_mm"),
            temperatura_min=Min("temperatura_min"),
            temperatura_max=Max("temperatura_max"),
            temperatura_media=Avg("temperatura_max"),
            evapotranspiracao_total=Sum("evapotranspiracao_mm"),
        )
        dados["alertas"] = AlertaClimatico.objects.filter(
            propriedade=propriedade,
            ativo=True,
        ).count()
        return Response(dados)


class PrevisaoHorariaViewSet(
    EscopoPropriedadeViewSetMixin,
    viewsets.ReadOnlyModelViewSet,
):
    queryset = PrevisaoHoraria.objects.select_related("propriedade").all()
    serializer_class = PrevisaoHorariaSerializer
    property_filter = "propriedade_id"
    property_path = "propriedade"
    filter_backends = (filters.OrderingFilter,)
    ordering_fields = ("data_hora", "temperatura", "precipitacao_mm", "vento_kmh")
    ordering = ("data_hora",)

    def get_queryset(self):
        queryset = super().get_queryset()
        propriedade = self.request.query_params.get("propriedade", "").strip()
        data_inicio = self.request.query_params.get("data_inicio", "").strip()
        data_fim = self.request.query_params.get("data_fim", "").strip()
        if propriedade:
            queryset = queryset.filter(propriedade_id=propriedade) if propriedade.isdecimal() else queryset.none()
        if data_inicio:
            queryset = queryset.filter(data_hora__gte=data_inicio)
        if data_fim:
            queryset = queryset.filter(data_hora__lte=data_fim)
        return queryset


class AlertaClimaticoViewSet(
    EscopoPropriedadeViewSetMixin,
    viewsets.ReadOnlyModelViewSet,
):
    queryset = AlertaClimatico.objects.select_related("propriedade", "talhao").all()
    serializer_class = AlertaClimaticoSerializer
    property_filter = "propriedade_id"
    property_path = "propriedade"
    action_roles = {"marcar_lido": PAPEIS_LEITURA}
    filter_backends = (filters.OrderingFilter,)
    ordering_fields = ("inicio", "nivel", "tipo")
    ordering = ("-inicio",)

    def get_queryset(self):
        queryset = super().get_queryset()
        propriedade = self.request.query_params.get("propriedade", "").strip()
        ativo = self.request.query_params.get("ativo", "").strip().lower()
        if propriedade:
            queryset = queryset.filter(propriedade_id=propriedade) if propriedade.isdecimal() else queryset.none()
        if ativo in {"true", "false"}:
            queryset = queryset.filter(ativo=ativo == "true")
        return queryset

    @action(detail=True, methods=["post"])
    def marcar_lido(self, request, pk=None):
        alerta = self.get_object()
        exigir_acesso_propriedade(
            request.user,
            alerta.propriedade,
            papeis=PAPEIS_LEITURA,
        )
        alerta.lido_em = timezone.now()
        alerta.save(update_fields=("lido_em", "atualizado_em"))
        return Response(self.get_serializer(alerta).data)


class AtualizacaoClimaViewSet(
    EscopoPropriedadeViewSetMixin,
    viewsets.ReadOnlyModelViewSet,
):
    queryset = AtualizacaoClima.objects.select_related("propriedade").all()
    serializer_class = AtualizacaoClimaSerializer
    property_filter = "propriedade_id"
    property_path = "propriedade"
    ordering = ("-iniciada_em",)

    def get_queryset(self):
        queryset = super().get_queryset()
        propriedade = self.request.query_params.get("propriedade", "").strip()
        if propriedade:
            queryset = queryset.filter(propriedade_id=propriedade) if propriedade.isdecimal() else queryset.none()
        return queryset


class ConfiguracaoClimaViewSet(
    EscopoPropriedadeViewSetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = ConfiguracaoClima.objects.select_related("propriedade").all()
    serializer_class = ConfiguracaoClimaSerializer
    property_filter = "propriedade_id"
    property_path = "propriedade"
    write_roles = PAPEIS_GESTAO

    def get_queryset(self):
        queryset = super().get_queryset()
        propriedade = self.request.query_params.get("propriedade", "").strip()
        if propriedade:
            queryset = queryset.filter(propriedade_id=propriedade) if propriedade.isdecimal() else queryset.none()
        return queryset

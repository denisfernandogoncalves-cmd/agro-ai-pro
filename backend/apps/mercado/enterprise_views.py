from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from apps.core.access import validar_filtro_propriedade

from .enterprise_analysis import analise_automatica, painel_mercado, serie_ativo
from .enterprise_models import (
    AtivoMercado,
    AtualizacaoMercado,
    ConfiguracaoAtivoMercado,
    CotacaoAtivoMercado,
)
from .enterprise_serializers import (
    AtualizacaoMercadoSerializer,
    ConfiguracaoAtivoMercadoSerializer,
    CotacaoAtivoMercadoSerializer,
)
from .enterprise_update import (
    ServicoMercadoEnterpriseError,
    atualizar_ativo,
    atualizar_todos,
    inicializar_configuracoes,
)


class CotacaoAtivoMercadoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CotacaoAtivoMercado.objects.all()
    serializer_class = CotacaoAtivoMercadoSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (filters.OrderingFilter,)
    ordering_fields = ("data_hora", "fechamento", "maxima", "minima", "ativo")

    def get_queryset(self):
        queryset = super().get_queryset()
        ativo = self.request.query_params.get("ativo", "").strip()
        intervalo = self.request.query_params.get("intervalo", "").strip()
        if ativo:
            queryset = queryset.filter(ativo=ativo)
        if intervalo:
            queryset = queryset.filter(intervalo=intervalo)
        return queryset

    @action(detail=False, methods=("get",))
    def serie(self, request):
        ativo = request.query_params.get("ativo", "").strip()
        janela = request.query_params.get("janela", "30d").strip()
        if ativo not in dict(AtivoMercado.choices):
            return Response({"detail": "Informe um ativo válido."}, status=status.HTTP_400_BAD_REQUEST)
        pontos = serie_ativo(ativo, janela)
        return Response(self.get_serializer(pontos, many=True).data)

    @action(detail=False, methods=("get",))
    def painel(self, request):
        propriedade_id = request.query_params.get("propriedade", "").strip()
        propriedade = validar_filtro_propriedade(request.user, propriedade_id) if propriedade_id else None
        return Response(painel_mercado(request.user, propriedade.pk if propriedade else None))

    @action(detail=False, methods=("get",))
    def analise(self, request):
        propriedade_id = request.query_params.get("propriedade", "").strip()
        propriedade = validar_filtro_propriedade(request.user, propriedade_id) if propriedade_id else None
        return Response(analise_automatica(request.user, propriedade.pk if propriedade else None))

    @action(detail=False, methods=("post",))
    def atualizar(self, request):
        ativo = str(request.data.get("ativo", "")).strip()
        try:
            if ativo:
                if ativo not in dict(AtivoMercado.choices):
                    return Response({"detail": "Ativo inválido."}, status=status.HTTP_400_BAD_REQUEST)
                resultado = atualizar_ativo(ativo, force=True)
            else:
                resultado = atualizar_todos(force=True)
        except ServicoMercadoEnterpriseError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response(resultado)


class ConfiguracaoAtivoMercadoViewSet(viewsets.ModelViewSet):
    queryset = ConfiguracaoAtivoMercado.objects.all()
    serializer_class = ConfiguracaoAtivoMercadoSerializer

    def get_permissions(self):
        if self.action in {"update", "partial_update"}:
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def get_queryset(self):
        inicializar_configuracoes()
        return super().get_queryset()

    def perform_create(self, serializer):
        raise PermissionError("As configurações são criadas automaticamente.")

    def perform_destroy(self, instance):
        raise PermissionError("Desative o ativo em vez de excluir sua configuração.")


class AtualizacaoMercadoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AtualizacaoMercado.objects.all()
    serializer_class = AtualizacaoMercadoSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (filters.OrderingFilter,)
    ordering_fields = ("iniciada_em", "status", "ativo")

    def get_queryset(self):
        queryset = super().get_queryset()
        ativo = self.request.query_params.get("ativo", "").strip()
        return queryset.filter(ativo=ativo) if ativo else queryset

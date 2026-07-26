from django.db.models.deletion import ProtectedError
from rest_framework import filters, status, viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import HistoricoAgronomico, Talhao
from .serializers import HistoricoAgronomicoSerializer, TalhaoSerializer


class TalhaoPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100

    def paginate_queryset(self, queryset, request, view=None):
        if "page" not in request.query_params and "page_size" not in request.query_params:
            return None
        return super().paginate_queryset(queryset, request, view)


class TalhaoViewSet(viewsets.ModelViewSet):
    queryset = Talhao.objects.select_related("propriedade").all().order_by("nome", "id")
    serializer_class = TalhaoSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = TalhaoPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["nome", "propriedade__nome", "cultura_atual", "safra", "tipo_solo"]
    ordering_fields = [
        "nome",
        "area_hectares",
        "cultura_atual",
        "safra",
        "produtividade_esperada",
        "produtividade_realizada",
        "criado_em",
        "atualizado_em",
    ]

    def get_queryset(self):
        queryset = super().get_queryset()
        propriedade = self.request.query_params.get("propriedade", "").strip()
        cultura = self.request.query_params.get("cultura", "").strip()
        safra = self.request.query_params.get("safra", "").strip()
        if propriedade:
            queryset = (
                queryset.filter(propriedade_id=propriedade)
                if propriedade.isdecimal()
                else queryset.none()
            )
        if cultura:
            queryset = queryset.filter(cultura_atual__iexact=cultura)
        if safra:
            queryset = queryset.filter(safra__iexact=safra)
        return queryset

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {
                    "detail": (
                        "O talhão possui histórico agronômico e não pode ser excluído."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )


class HistoricoAgronomicoViewSet(viewsets.ModelViewSet):
    queryset = HistoricoAgronomico.objects.select_related(
        "talhao", "talhao__propriedade"
    ).all()
    serializer_class = HistoricoAgronomicoSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = TalhaoPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["talhao__nome", "cultura", "safra", "observacoes"]
    ordering_fields = ["data_referencia", "cultura", "safra", "criado_em"]

    def get_queryset(self):
        queryset = super().get_queryset()
        talhao = self.request.query_params.get("talhao", "").strip()
        if talhao:
            queryset = (
                queryset.filter(talhao_id=talhao)
                if talhao.isdecimal()
                else queryset.none()
            )
        return queryset

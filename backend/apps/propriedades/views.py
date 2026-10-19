from django.db.models.deletion import ProtectedError
from rest_framework import filters, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.core.pagination import PaginacaoOpcional

from .models import Propriedade
from .serializers import PropriedadeSerializer


class PropriedadeViewSet(viewsets.ModelViewSet):
    queryset = Propriedade.objects.prefetch_related(
        "vinculos_cadpro__cad_pro",
        "linhas_importacao",
    ).order_by("nome", "id")
    serializer_class = PropriedadeSerializer
    pagination_class = PaginacaoOpcional
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["nome", "apelido", "proprietario", "municipio", "uf", "cad_pro_identificacao", "vinculos_cadpro__cad_pro__codigo"]
    ordering_fields = ["nome", "municipio", "area_hectares", "criado_em"]

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {"detail": "A propriedade possui talhões e não pode ser excluída."},
                status=status.HTTP_409_CONFLICT,
            )

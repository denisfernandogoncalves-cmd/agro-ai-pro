from django.db.models.deletion import ProtectedError
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.access import (
    PAPEL_ADMINISTRADOR,
    PAPEIS_GESTAO,
    filtrar_queryset_por_usuario,
    pode_criar_propriedade,
)
from apps.core.permissions import PapelPropriedadePermission
from apps.core.viewsets import EscopoPropriedadeViewSetMixin

from .models import AcessoPropriedade, Propriedade
from .serializers import AcessoPropriedadeSerializer, PropriedadeSerializer


class PropriedadeViewSet(viewsets.ModelViewSet):
    queryset = Propriedade.objects.all().order_by("nome", "id")
    serializer_class = PropriedadeSerializer
    permission_classes = (IsAuthenticated, PapelPropriedadePermission)
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    search_fields = ("nome", "proprietario", "municipio", "uf")
    ordering_fields = ("nome", "municipio", "area_hectares", "criado_em")
    property_path = ""
    action_roles = {
        "update": PAPEIS_GESTAO,
        "partial_update": PAPEIS_GESTAO,
        "destroy": (PAPEL_ADMINISTRADOR,),
    }

    def get_roles_for_action(self, action):
        return self.action_roles.get(action, PAPEIS_GESTAO)

    def get_queryset(self):
        return filtrar_queryset_por_usuario(
            super().get_queryset(),
            self.request.user,
            "id",
        )

    def perform_create(self, serializer):
        if not pode_criar_propriedade(self.request.user):
            raise PermissionDenied(
                "Novas propriedades devem ser criadas por um superusuário "
                "ou por um usuário ainda sem vínculos."
            )
        propriedade = serializer.save()
        if not self.request.user.is_superuser:
            AcessoPropriedade.objects.create(
                propriedade=propriedade,
                usuario=self.request.user,
                papel=AcessoPropriedade.Papel.ADMINISTRADOR,
            )

    @action(detail=False, methods=["get"])
    def permissoes(self, request):
        return Response(
            {
                "pode_criar_propriedade": pode_criar_propriedade(request.user),
                "superusuario": request.user.is_superuser,
            }
        )

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {"detail": "A propriedade possui vínculos e não pode ser excluída."},
                status=status.HTTP_409_CONFLICT,
            )


class AcessoPropriedadeViewSet(
    EscopoPropriedadeViewSetMixin,
    viewsets.ModelViewSet,
):
    queryset = AcessoPropriedade.objects.select_related(
        "propriedade",
        "usuario",
    )
    serializer_class = AcessoPropriedadeSerializer
    property_filter = "propriedade_id"
    property_path = "propriedade"
    property_input_path = "propriedade"
    write_roles = (PAPEL_ADMINISTRADOR,)
    action_roles = {
        "create": (PAPEL_ADMINISTRADOR,),
        "update": (PAPEL_ADMINISTRADOR,),
        "partial_update": (PAPEL_ADMINISTRADOR,),
        "destroy": (PAPEL_ADMINISTRADOR,),
    }
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    search_fields = (
        "usuario__username",
        "usuario__first_name",
        "usuario__last_name",
        "propriedade__nome",
        "papel",
    )
    ordering_fields = ("propriedade__nome", "usuario__username", "papel")

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_superuser:
            return queryset
        ids_administrados = AcessoPropriedade.objects.filter(
            usuario=self.request.user,
            papel=AcessoPropriedade.Papel.ADMINISTRADOR,
            ativo=True,
        ).values_list("propriedade_id", flat=True)
        return queryset.filter(propriedade_id__in=ids_administrados)

    def perform_destroy(self, instance):
        if (
            instance.usuario_id == self.request.user.id
            and instance.papel == AcessoPropriedade.Papel.ADMINISTRADOR
        ):
            outros = AcessoPropriedade.objects.filter(
                propriedade=instance.propriedade,
                papel=AcessoPropriedade.Papel.ADMINISTRADOR,
                ativo=True,
            ).exclude(pk=instance.pk)
            if not outros.exists() and not self.request.user.is_superuser:
                raise PermissionDenied(
                    "A propriedade deve manter ao menos um administrador ativo."
                )
        super().perform_destroy(instance)

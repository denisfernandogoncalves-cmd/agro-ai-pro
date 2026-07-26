from rest_framework.permissions import IsAuthenticated

from .access import (
    PAPEIS_GESTAO,
    exigir_acesso_propriedade,
    filtrar_queryset_por_usuario,
    resolver_caminho_serializer,
)
from .permissions import PapelGlobalPermission, PapelPropriedadePermission


class EscopoPropriedadeViewSetMixin:
    property_filter = "propriedade_id"
    property_path = "propriedade"
    property_input_path = None
    write_roles = PAPEIS_GESTAO
    action_roles = {}
    permission_classes = (IsAuthenticated, PapelPropriedadePermission)

    def get_roles_for_action(self, action):
        return self.action_roles.get(action, self.write_roles)

    def get_queryset(self):
        queryset = super().get_queryset()
        return filtrar_queryset_por_usuario(
            queryset,
            self.request.user,
            self.property_filter,
        )

    def _propriedade_do_serializer(self, serializer):
        caminho = self.property_input_path or self.property_path
        return resolver_caminho_serializer(serializer, caminho)

    def perform_create(self, serializer):
        propriedade = self._propriedade_do_serializer(serializer)
        exigir_acesso_propriedade(
            self.request.user,
            propriedade,
            papeis=self.get_roles_for_action("create"),
        )
        serializer.save()

    def perform_update(self, serializer):
        propriedade = self._propriedade_do_serializer(serializer)
        exigir_acesso_propriedade(
            self.request.user,
            propriedade,
            papeis=self.get_roles_for_action(self.action),
        )
        serializer.save()


class EscopoGlobalViewSetMixin:
    write_roles = PAPEIS_GESTAO
    action_roles = {}
    permission_classes = (IsAuthenticated, PapelGlobalPermission)

    def get_roles_for_action(self, action):
        return self.action_roles.get(action, self.write_roles)

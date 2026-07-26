from rest_framework.permissions import BasePermission, SAFE_METHODS

from .access import (
    PAPEIS_GESTAO,
    resolver_caminho,
    usuario_tem_papel,
    papel_na_propriedade,
)


class PapelPropriedadePermission(BasePermission):
    message = "Seu perfil não permite executar esta ação."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        if getattr(view, "action", None) == "create":
            return True
        if not getattr(view, "detail", False):
            papeis = getattr(view, "non_object_action_roles", {}).get(
                getattr(view, "action", None)
            )
            return True if papeis is None else usuario_tem_papel(request.user, papeis)
        return True

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS or request.user.is_superuser:
            return True
        propriedade = resolver_caminho(
            obj,
            getattr(view, "property_path", "propriedade"),
        )
        papel = papel_na_propriedade(request.user, propriedade)
        papeis = view.get_roles_for_action(getattr(view, "action", None))
        return bool(papel and papel in papeis)


class PapelGlobalPermission(BasePermission):
    message = "Seu perfil não permite alterar este cadastro global."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS or request.user.is_superuser:
            return True
        papeis = view.get_roles_for_action(getattr(view, "action", None))
        return usuario_tem_papel(request.user, papeis or PAPEIS_GESTAO)

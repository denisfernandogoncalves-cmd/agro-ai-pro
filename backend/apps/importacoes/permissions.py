from rest_framework.permissions import BasePermission


class PodeConfirmarImportacao(BasePermission):
    message = "O usuário não possui permissão para confirmar importações."

    def has_permission(self, request, view):
        return request.user.has_perm("importacoes.confirmar_loteimportacao")

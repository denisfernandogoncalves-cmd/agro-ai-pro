from django.conf import settings
from django.db import models


class AcessoUsuario(models.Model):
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="acesso_modulos")
    # Ausência de configuração preserva os acessos das contas anteriores.
    modulos = models.JSONField(null=True, blank=True, default=None)
    permissoes = models.JSONField(null=True, blank=True, default=None)
    excluido_em = models.DateTimeField(null=True, blank=True)

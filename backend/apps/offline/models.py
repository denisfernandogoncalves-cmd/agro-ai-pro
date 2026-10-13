from django.conf import settings
from django.db import models


class ReciboSincronizacao(models.Model):
    """Confirmação persistente, gravada na mesma transação que a operação."""

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    operacao = models.UUIDField()
    dispositivo = models.UUIDField()
    hash_payload = models.CharField(max_length=64)
    resultado = models.JSONField()
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=("usuario", "operacao"), name="offline_usuario_operacao_unica",
        )]

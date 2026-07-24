from django.db import models
from apps.propriedades.models import Propriedade


class PrevisaoClima(models.Model):

    propriedade = models.ForeignKey(
        Propriedade,
        on_delete=models.CASCADE,
        related_name="previsoes_clima"
    )

    data = models.DateField()

    temperatura_min = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    temperatura_max = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    chuva_mm = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True
    )

    umidade = models.IntegerField(
        null=True,
        blank=True
    )

    vento_kmh = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True
    )

    condicao = models.CharField(
        max_length=100,
        blank=True
    )

    alerta_agricola = models.TextField(
        blank=True
    )

    criado_em = models.DateTimeField(
        auto_now_add=True
    )


    def __str__(self):
        return f"{self.propriedade.nome} - {self.data}"
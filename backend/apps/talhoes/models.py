from django.db import models
from apps.propriedades.models import Propriedade


class Talhao(models.Model):

    propriedade = models.ForeignKey(
        Propriedade,
        on_delete=models.CASCADE,
        related_name="talhoes"
    )

    nome = models.CharField(
        max_length=100
    )

    area_hectares = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    arquivo_kml = models.FileField(
        upload_to="talhoes/kml/",
        null=True,
        blank=True
    )

    latitude_centro = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True
    )

    longitude_centro = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True
    )

    cultura_atual = models.CharField(
        max_length=50,
        blank=True
    )

    safra = models.CharField(
        max_length=20,
        blank=True
    )

    tipo_solo = models.CharField(
        max_length=100,
        blank=True
    )

    altitude_media = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True
    )

    declividade_media = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True
    )

    produtividade_esperada = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    observacoes = models.TextField(
        blank=True
    )

    criado_em = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.nome} - {self.propriedade.nome}"
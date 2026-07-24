from django.db import models


class Propriedade(models.Model):

    nome = models.CharField(
        max_length=100
    )

    proprietario = models.CharField(
        max_length=100,
        blank=True
    )

    municipio = models.CharField(
        max_length=100
    )

    uf = models.CharField(
        max_length=2,
        blank=True
    )

    area_hectares = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True
    )

    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True
    )

    arquivo_kml = models.FileField(
        upload_to="kml/",
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
        return self.nome
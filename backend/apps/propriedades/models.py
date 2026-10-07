from django.db import models
from django.core.validators import RegexValidator


class Propriedade(models.Model):

    bp_cvale = models.CharField(
        max_length=40, blank=True, default="",
        validators=[RegexValidator(r"^[0-9]*\Z", "Informe somente números no BP da C.Vale.")],
        help_text="BP/BEP da propriedade, utilizado exclusivamente no faturamento C.Vale.",
    )

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

    geometria_geojson = models.JSONField(
        null=True,
        blank=True,
        editable=False
    )

    area_calculada_hectares = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        editable=False
    )

    observacoes = models.TextField(
        blank=True
    )

    criado_em = models.DateTimeField(
        auto_now_add=True
    )


    def __str__(self):
        return self.nome

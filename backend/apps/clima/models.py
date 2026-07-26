from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from apps.propriedades.models import Propriedade


class PrevisaoClima(models.Model):
    class Meta:
        ordering = ("data", "propriedade_id")
        constraints = [
            models.UniqueConstraint(
                fields=("propriedade", "data"),
                name="clima_previsao_unica_por_propriedade_data",
            ),
            models.CheckConstraint(
                condition=models.Q(chuva_mm__gte=0) | models.Q(chuva_mm__isnull=True),
                name="clima_chuva_nao_negativa",
            ),
            models.CheckConstraint(
                condition=models.Q(vento_kmh__gte=0) | models.Q(vento_kmh__isnull=True),
                name="clima_vento_nao_negativo",
            ),
        ]

    propriedade = models.ForeignKey(
        Propriedade,
        on_delete=models.PROTECT,
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
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
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

    probabilidade_chuva = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )

    codigo_tempo = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )

    alerta_agricola = models.TextField(
        blank=True
    )

    fonte = models.CharField(
        max_length=50,
        default="Open-Meteo",
    )

    criado_em = models.DateTimeField(
        auto_now_add=True
    )

    atualizado_em = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"{self.propriedade.nome} - {self.data}"

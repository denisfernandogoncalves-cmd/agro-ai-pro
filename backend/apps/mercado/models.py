from django.core.validators import MinValueValidator
from django.db import models


class CotacaoMercado(models.Model):
    class Produto(models.TextChoices):
        SOJA = "soja", "Soja"
        MILHO = "milho", "Milho"
        TRIGO = "trigo", "Trigo"
        BRENT = "brent", "Petróleo Brent"

    produto = models.CharField(max_length=20, choices=Produto.choices)
    data = models.DateField()
    valor = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        validators=[MinValueValidator(0)],
    )
    unidade = models.CharField(max_length=50)
    fonte = models.CharField(max_length=80, default="FRED / FMI")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("produto", "data")
        constraints = [
            models.UniqueConstraint(
                fields=("produto", "data"),
                name="mercado_cotacao_unica_produto_data",
            ),
            models.CheckConstraint(
                condition=models.Q(valor__gte=0),
                name="mercado_cotacao_valor_nao_negativo",
            ),
        ]
        indexes = [
            models.Index(fields=("produto", "-data"), name="mercado_prod_data_idx"),
        ]

    def __str__(self):
        return f"{self.get_produto_display()} - {self.data}"


class ClimaCornBelt(models.Model):
    class Regiao(models.TextChoices):
        IOWA = "iowa", "Iowa"
        ILLINOIS = "illinois", "Illinois"
        INDIANA = "indiana", "Indiana"
        NEBRASKA = "nebraska", "Nebraska"
        MINNESOTA = "minnesota", "Minnesota"

    regiao = models.CharField(max_length=20, choices=Regiao.choices)
    data = models.DateField()
    temperatura_min = models.DecimalField(max_digits=5, decimal_places=2)
    temperatura_max = models.DecimalField(max_digits=5, decimal_places=2)
    precipitacao_mm = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    alerta = models.CharField(max_length=160, blank=True)
    fonte = models.CharField(max_length=50, default="Open-Meteo")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("regiao", "data")
        constraints = [
            models.UniqueConstraint(
                fields=("regiao", "data"),
                name="mercado_corn_belt_unico_regiao_data",
            ),
            models.CheckConstraint(
                condition=models.Q(precipitacao_mm__gte=0),
                name="mercado_corn_belt_chuva_nao_negativa",
            ),
        ]

    def __str__(self):
        return f"{self.get_regiao_display()} - {self.data}"


class NoticiaMercado(models.Model):
    titulo = models.CharField(max_length=220)
    resumo = models.TextField(blank=True)
    fonte = models.CharField(max_length=100)
    url = models.URLField(max_length=500)
    publicada_em = models.DateTimeField()
    ativa = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-publicada_em", "-id")

    def __str__(self):
        return self.titulo


from .enterprise_models import (  # noqa: E402,F401
    AtivoMercado,
    AtualizacaoMercado,
    ConfiguracaoAtivoMercado,
    CotacaoAtivoMercado,
)

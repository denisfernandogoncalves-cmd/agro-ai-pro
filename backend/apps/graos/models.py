from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from apps.propriedades.models import Propriedade
from apps.talhoes.models import Talhao


class ArmazemGraos(models.Model):
    propriedade = models.ForeignKey(
        Propriedade,
        on_delete=models.PROTECT,
        related_name="armazens_graos",
    )
    nome = models.CharField(max_length=120)
    capacidade_kg = models.DecimalField(
        max_digits=16,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
    )
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("nome", "id")
        verbose_name = "armazém de grãos"
        verbose_name_plural = "armazéns de grãos"
        constraints = [
            models.UniqueConstraint(
                fields=("propriedade", "nome"),
                name="graos_armazem_nome_propriedade_unico",
            ),
            models.CheckConstraint(
                condition=models.Q(capacidade_kg__gt=0),
                name="graos_armazem_capacidade_positiva",
            ),
        ]

    def __str__(self):
        return f"{self.nome} - {self.propriedade.nome}"


class LoteGraos(models.Model):
    armazem = models.ForeignKey(
        ArmazemGraos,
        on_delete=models.PROTECT,
        related_name="lotes",
    )
    talhao = models.ForeignKey(
        Talhao,
        on_delete=models.PROTECT,
        related_name="lotes_graos",
        null=True,
        blank=True,
    )
    codigo = models.CharField(max_length=100)
    cultura = models.CharField(max_length=50)
    safra = models.CharField(max_length=20)
    umidade_percentual = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal("0")),
            MaxValueValidator(Decimal("100")),
        ],
    )
    impureza_percentual = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal("0")),
            MaxValueValidator(Decimal("100")),
        ],
    )
    ativo = models.BooleanField(default=True)
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("safra", "cultura", "codigo", "id")
        verbose_name = "lote de grãos"
        verbose_name_plural = "lotes de grãos"
        indexes = [
            models.Index(
                fields=("safra", "cultura"),
                name="graos_lote_safra_cultura_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=("armazem", "codigo"),
                name="graos_lote_codigo_armazem_unico",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(umidade_percentual__isnull=True)
                    | models.Q(
                        umidade_percentual__gte=0,
                        umidade_percentual__lte=100,
                    )
                ),
                name="graos_lote_umidade_valida",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(impureza_percentual__isnull=True)
                    | models.Q(
                        impureza_percentual__gte=0,
                        impureza_percentual__lte=100,
                    )
                ),
                name="graos_lote_impureza_valida",
            ),
        ]

    @property
    def propriedade_id(self):
        return self.armazem.propriedade_id

    def clean(self):
        super().clean()
        if (
            self.talhao_id
            and self.armazem_id
            and self.talhao.propriedade_id != self.armazem.propriedade_id
        ):
            raise ValidationError(
                {"talhao": "O talhão e o armazém devem pertencer à mesma propriedade."}
            )

    def __str__(self):
        return f"{self.codigo} - {self.cultura} ({self.safra})"


class MovimentacaoGraos(models.Model):
    class Tipo(models.TextChoices):
        ENTRADA = "entrada", "Entrada"
        SAIDA = "saida", "Saída"

    tipo = models.CharField(max_length=8, choices=Tipo.choices)
    lote = models.ForeignKey(
        LoteGraos,
        on_delete=models.PROTECT,
        related_name="movimentacoes",
    )
    quantidade_kg = models.DecimalField(
        max_digits=16,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
    )
    data_movimento = models.DateField(default=timezone.localdate)
    referencia_externa = models.CharField(max_length=120, blank=True)
    chave_idempotencia = models.CharField(
        max_length=160,
        unique=True,
        null=True,
        blank=True,
        editable=False,
    )
    observacoes = models.TextField(blank=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="movimentacoes_graos",
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-data_movimento", "-id")
        verbose_name = "movimentação de grãos"
        verbose_name_plural = "movimentações de grãos"
        indexes = [
            models.Index(
                fields=("lote", "data_movimento"),
                name="graos_movimento_lote_data_idx",
            ),
            models.Index(
                fields=("referencia_externa",),
                name="graos_movimento_referencia_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantidade_kg__gt=0),
                name="graos_movimento_quantidade_positiva",
            ),
        ]

    def save(self, *args, **kwargs):
        self.chave_idempotencia = self.chave_idempotencia or None
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.lote} - {self.quantidade_kg} kg"

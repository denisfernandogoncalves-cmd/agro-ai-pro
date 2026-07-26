from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from apps.propriedades.models import Propriedade


class Talhao(models.Model):

    class Meta:
        constraints = [
            models.CheckConstraint(check=models.Q(area_hectares__gt=0), name="talhao_area_positiva"),
            models.CheckConstraint(
                check=models.Q(produtividade_esperada__gte=0)
                | models.Q(produtividade_esperada__isnull=True),
                name="talhao_produtividade_esperada_nao_negativa",
            ),
            models.CheckConstraint(
                check=models.Q(produtividade_realizada__gte=0)
                | models.Q(produtividade_realizada__isnull=True),
                name="talhao_produtividade_realizada_nao_negativa",
            ),
        ]

    propriedade = models.ForeignKey(
        Propriedade,
        on_delete=models.PROTECT,
        related_name="talhoes"
    )

    nome = models.CharField(
        max_length=100
    )

    area_hectares = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
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
        blank=True,
        validators=[MinValueValidator(Decimal("-90")), MaxValueValidator(Decimal("90"))],
    )

    longitude_centro = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("-180")), MaxValueValidator(Decimal("180"))],
    )

    geometria_geojson = models.JSONField(null=True, blank=True, editable=False)

    area_calculada_hectares = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        editable=False,
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
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )

    produtividade_realizada = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )

    observacoes = models.TextField(
        blank=True
    )

    criado_em = models.DateTimeField(
        auto_now_add=True
    )

    atualizado_em = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"{self.nome} - {self.propriedade.nome}"

    def clean(self):
        super().clean()
        erros = {}
        if not self.propriedade_id:
            erros["propriedade"] = "A propriedade é obrigatória."
        if self.area_hectares is not None and self.area_hectares <= 0:
            erros["area_hectares"] = "A área do talhão deve ser maior que zero."
        if self.propriedade_id and self.area_hectares is not None:
            outros = Talhao.objects.filter(propriedade_id=self.propriedade_id)
            if self.pk:
                outros = outros.exclude(pk=self.pk)
            total = outros.aggregate(models.Sum("area_hectares"))["area_hectares__sum"] or Decimal("0")
            if total + self.area_hectares > self.propriedade.area_hectares:
                erros["area_hectares"] = (
                    "A soma das áreas dos talhões não pode ultrapassar a área da propriedade. "
                    f"Disponível: {self.propriedade.area_hectares - total:.2f} ha."
                )
        if erros:
            raise ValidationError(erros)


class HistoricoAgronomico(models.Model):
    class Meta:
        ordering = ("-data_referencia", "-id")
        verbose_name = "histórico agronômico"
        verbose_name_plural = "históricos agronômicos"
        constraints = [
            models.CheckConstraint(
                check=models.Q(produtividade_esperada__gte=0)
                | models.Q(produtividade_esperada__isnull=True),
                name="historico_produtividade_esperada_nao_negativa",
            ),
            models.CheckConstraint(
                check=models.Q(produtividade_realizada__gte=0)
                | models.Q(produtividade_realizada__isnull=True),
                name="historico_produtividade_realizada_nao_negativa",
            ),
        ]

    talhao = models.ForeignKey(
        Talhao,
        on_delete=models.PROTECT,
        related_name="historicos_agronomicos",
    )
    data_referencia = models.DateField()
    cultura = models.CharField(max_length=50, blank=True)
    safra = models.CharField(max_length=20, blank=True)
    produtividade_esperada = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    produtividade_realizada = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        data = self.data_referencia
        data_formatada = data.strftime("%d/%m/%Y") if hasattr(data, "strftime") else str(data)
        return f"{self.talhao.nome} - {data_formatada}"

    def clean(self):
        super().clean()
        possui_conteudo = any(
            (
                self.cultura.strip(),
                self.safra.strip(),
                self.produtividade_esperada is not None,
                self.produtividade_realizada is not None,
                self.observacoes.strip(),
            )
        )
        if not possui_conteudo:
            raise ValidationError(
                "Informe ao menos um dado agronômico além da data de referência."
            )

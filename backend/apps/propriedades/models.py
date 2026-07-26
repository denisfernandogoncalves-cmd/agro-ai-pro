from django.conf import settings
from django.db import models


class Propriedade(models.Model):
    nome = models.CharField(max_length=100)
    proprietario = models.CharField(max_length=100, blank=True)
    municipio = models.CharField(max_length=100)
    uf = models.CharField(max_length=2, blank=True)
    area_hectares = models.DecimalField(max_digits=10, decimal_places=2)
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True,
    )
    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True,
    )
    arquivo_kml = models.FileField(
        upload_to="kml/",
        null=True,
        blank=True,
    )
    geometria_geojson = models.JSONField(
        null=True,
        blank=True,
        editable=False,
    )
    area_calculada_hectares = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        editable=False,
    )
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome


class AcessoPropriedade(models.Model):
    class Papel(models.TextChoices):
        ADMINISTRADOR = "administrador", "Administrador"
        GESTOR = "gestor", "Gestor"
        OPERADOR = "operador", "Operador"
        LEITURA = "leitura", "Somente leitura"

    propriedade = models.ForeignKey(
        Propriedade,
        on_delete=models.CASCADE,
        related_name="acessos",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="acessos_propriedades",
    )
    papel = models.CharField(
        max_length=16,
        choices=Papel.choices,
        default=Papel.LEITURA,
    )
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("propriedade__nome", "usuario__username")
        constraints = [
            models.UniqueConstraint(
                fields=("propriedade", "usuario"),
                name="propriedade_usuario_acesso_unico",
            )
        ]
        indexes = [
            models.Index(
                fields=("usuario", "ativo"),
                name="prop_acesso_usuario_idx",
            ),
            models.Index(
                fields=("propriedade", "papel"),
                name="prop_acesso_papel_idx",
            ),
        ]

    def __str__(self):
        return f"{self.usuario} - {self.propriedade} ({self.get_papel_display()})"

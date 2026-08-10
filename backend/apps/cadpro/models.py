import re
import unicodedata
import uuid

from django.core.exceptions import ValidationError
from django.db import models

from apps.propriedades.models import Propriedade


def normalizar_codigo_cadpro(codigo):
    """Produz a chave canônica de um código CAD/PRO."""
    texto = unicodedata.normalize("NFKD", str(codigo or "").strip())
    texto = "".join(
        caractere for caractere in texto if not unicodedata.combining(caractere)
    ).upper()
    return re.sub(r"[^A-Z0-9]", "", texto)


class CADPro(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo = models.CharField(max_length=50)
    codigo_normalizado = models.CharField(
        max_length=50,
        unique=True,
        editable=False,
    )
    descricao = models.CharField(max_length=255)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("codigo_normalizado", "id")
        verbose_name = "CAD/PRO"
        verbose_name_plural = "CAD/PROs"

    def clean(self):
        super().clean()
        self.codigo = " ".join(str(self.codigo or "").strip().split())
        self.descricao = " ".join(str(self.descricao or "").strip().split())
        self.codigo_normalizado = normalizar_codigo_cadpro(self.codigo)
        erros = {}
        if not self.codigo_normalizado:
            erros["codigo"] = "Informe um código CAD/PRO com letras ou números."
        if not self.descricao:
            erros["descricao"] = "Informe a descrição do CAD/PRO."
        if erros:
            raise ValidationError(erros)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.codigo} - {self.descricao}"


class CADProPropriedade(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cad_pro = models.ForeignKey(
        CADPro,
        on_delete=models.PROTECT,
        related_name="vinculos_propriedades",
    )
    propriedade = models.ForeignKey(
        Propriedade,
        on_delete=models.PROTECT,
        related_name="vinculos_cadpro",
    )
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("propriedade__nome", "id")
        verbose_name = "vínculo CAD/PRO e propriedade"
        verbose_name_plural = "vínculos CAD/PRO e propriedades"
        constraints = [
            models.UniqueConstraint(
                fields=("cad_pro", "propriedade"),
                name="cadpro_cad_pro_propriedade_unico",
            ),
        ]

    def clean(self):
        super().clean()
        novo_ou_reativado = self._state.adding
        if self.pk and self.ativo and not self._state.adding:
            novo_ou_reativado = not CADProPropriedade.objects.filter(
                pk=self.pk,
                ativo=True,
            ).exists()
        if self.cad_pro_id and novo_ou_reativado and not self.cad_pro.ativo:
            raise ValidationError(
                {"cad_pro": "Não é possível vincular uma propriedade a um CAD/PRO inativo."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.cad_pro.codigo} - {self.propriedade.nome}"

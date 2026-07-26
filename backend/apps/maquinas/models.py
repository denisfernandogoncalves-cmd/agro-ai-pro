from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.producao.models import OperacaoAgricola
from apps.propriedades.models import Propriedade


class Maquina(models.Model):
    class Tipo(models.TextChoices):
        TRATOR = "trator", "Trator"
        COLHEITADEIRA = "colheitadeira", "Colheitadeira"
        PULVERIZADOR = "pulverizador", "Pulverizador"
        IMPLEMENTO = "implemento", "Implemento"
        CAMINHAO = "caminhao", "Caminhão"
        OUTRO = "outro", "Outro"

    class Status(models.TextChoices):
        ATIVA = "ativa", "Ativa"
        MANUTENCAO = "manutencao", "Em manutenção"
        INATIVA = "inativa", "Inativa"

    identificacao = models.CharField(max_length=80, unique=True)
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    marca = models.CharField(max_length=80, blank=True)
    modelo = models.CharField(max_length=100, blank=True)
    ano = models.PositiveSmallIntegerField(null=True, blank=True)
    propriedade = models.ForeignKey(
        Propriedade,
        on_delete=models.PROTECT,
        related_name="maquinas",
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.ATIVA,
    )
    horimetro_atual = models.DecimalField(
        max_digits=12,
        decimal_places=1,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("identificacao",)

    def __str__(self):
        return self.identificacao


class UsoMaquina(models.Model):
    maquina = models.ForeignKey(
        Maquina,
        on_delete=models.PROTECT,
        related_name="usos",
    )
    operacao = models.ForeignKey(
        OperacaoAgricola,
        on_delete=models.PROTECT,
        related_name="maquinas_utilizadas",
    )
    operador = models.CharField(max_length=120, blank=True)
    data = models.DateField(default=timezone.localdate)
    horimetro_inicial = models.DecimalField(max_digits=12, decimal_places=1)
    horimetro_final = models.DecimalField(max_digits=12, decimal_places=1)
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-data", "-id")

    @property
    def horas_trabalhadas(self):
        return self.horimetro_final - self.horimetro_inicial

    def clean(self):
        erros = {}
        if self.horimetro_final <= self.horimetro_inicial:
            erros["horimetro_final"] = "O horímetro final deve superar o inicial."
        if self.maquina_id and self.maquina.status != Maquina.Status.ATIVA:
            erros["maquina"] = "Somente máquinas ativas podem ser utilizadas."
        if erros:
            raise ValidationError(erros)


class AbastecimentoMaquina(models.Model):
    maquina = models.ForeignKey(
        Maquina,
        on_delete=models.PROTECT,
        related_name="abastecimentos",
    )
    data = models.DateField(default=timezone.localdate)
    litros = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    valor_total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    horimetro = models.DecimalField(max_digits=12, decimal_places=1)
    documento = models.CharField(max_length=80, blank=True)
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-data", "-id")


class ManutencaoMaquina(models.Model):
    class Status(models.TextChoices):
        AGENDADA = "agendada", "Agendada"
        CONCLUIDA = "concluida", "Concluída"
        CANCELADA = "cancelada", "Cancelada"

    maquina = models.ForeignKey(
        Maquina,
        on_delete=models.PROTECT,
        related_name="manutencoes",
    )
    descricao = models.CharField(max_length=220)
    data_prevista = models.DateField()
    horimetro_previsto = models.DecimalField(
        max_digits=12, decimal_places=1, null=True, blank=True
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.AGENDADA,
    )
    data_conclusao = models.DateField(null=True, blank=True)
    horimetro_realizado = models.DecimalField(
        max_digits=12, decimal_places=1, null=True, blank=True
    )
    custo = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("data_prevista", "id")

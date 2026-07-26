from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.propriedades.models import Propriedade


class CategoriaFinanceira(models.Model):
    class Aplicacao(models.TextChoices):
        DESPESA = "despesa", "Despesa"
        RECEITA = "receita", "Receita"
        AMBOS = "ambos", "Ambos"

    nome = models.CharField(max_length=100, unique=True)
    aplicacao = models.CharField(
        max_length=10,
        choices=Aplicacao.choices,
        default=Aplicacao.AMBOS,
    )
    ativa = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("nome",)

    def __str__(self):
        return self.nome


class ParceiroFinanceiro(models.Model):
    class Tipo(models.TextChoices):
        FORNECEDOR = "fornecedor", "Fornecedor"
        CLIENTE = "cliente", "Cliente"
        AMBOS = "ambos", "Ambos"

    nome = models.CharField(max_length=160)
    tipo = models.CharField(max_length=12, choices=Tipo.choices)
    documento = models.CharField(max_length=20, blank=True, unique=True, null=True)
    email = models.EmailField(blank=True)
    telefone = models.CharField(max_length=30, blank=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("nome",)

    def save(self, *args, **kwargs):
        self.documento = self.documento or None
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nome


class CentroCusto(models.Model):
    nome = models.CharField(max_length=120)
    propriedade = models.ForeignKey(
        Propriedade,
        on_delete=models.PROTECT,
        related_name="centros_custo",
        null=True,
        blank=True,
    )
    safra = models.CharField(max_length=20, blank=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("nome",)
        constraints = [
            models.UniqueConstraint(
                fields=("nome", "propriedade", "safra"),
                name="financeiro_centro_unico_contexto",
            )
        ]

    def __str__(self):
        return self.nome


class LancamentoFinanceiro(models.Model):
    class Tipo(models.TextChoices):
        PAGAR = "pagar", "Conta a pagar"
        RECEBER = "receber", "Conta a receber"

    class Status(models.TextChoices):
        PENDENTE = "pendente", "Pendente"
        LIQUIDADO = "liquidado", "Liquidado"
        CANCELADO = "cancelado", "Cancelado"

    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    descricao = models.CharField(max_length=220)
    valor = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    categoria = models.ForeignKey(
        CategoriaFinanceira,
        on_delete=models.PROTECT,
        related_name="lancamentos",
    )
    parceiro = models.ForeignKey(
        ParceiroFinanceiro,
        on_delete=models.PROTECT,
        related_name="lancamentos",
        null=True,
        blank=True,
    )
    centro_custo = models.ForeignKey(
        CentroCusto,
        on_delete=models.PROTECT,
        related_name="lancamentos",
        null=True,
        blank=True,
    )
    propriedade = models.ForeignKey(
        Propriedade,
        on_delete=models.PROTECT,
        related_name="lancamentos_financeiros",
        null=True,
        blank=True,
    )
    safra = models.CharField(max_length=20, blank=True)
    data_emissao = models.DateField(default=timezone.localdate)
    data_vencimento = models.DateField()
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.PENDENTE,
    )
    data_liquidacao = models.DateField(null=True, blank=True)
    valor_liquidado = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("data_vencimento", "id")
        indexes = [
            models.Index(
                fields=("tipo", "status", "data_vencimento"),
                name="financeiro_tipo_status_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(valor__gt=0),
                name="financeiro_valor_positivo",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(valor_liquidado__isnull=True)
                    | models.Q(valor_liquidado__gt=0)
                ),
                name="financeiro_liquidado_positivo",
            ),
        ]

    @property
    def atrasado(self):
        return (
            self.status == self.Status.PENDENTE
            and self.data_vencimento < timezone.localdate()
        )

    def clean(self):
        erros = {}
        if self.tipo == self.Tipo.PAGAR and self.categoria.aplicacao == CategoriaFinanceira.Aplicacao.RECEITA:
            erros["categoria"] = "Escolha uma categoria de despesa ou de ambos."
        if self.tipo == self.Tipo.RECEBER and self.categoria.aplicacao == CategoriaFinanceira.Aplicacao.DESPESA:
            erros["categoria"] = "Escolha uma categoria de receita ou de ambos."
        if self.status == self.Status.LIQUIDADO:
            if not self.data_liquidacao:
                erros["data_liquidacao"] = "Informe a data da liquidação."
            if not self.valor_liquidado:
                erros["valor_liquidado"] = "Informe o valor liquidado."
        elif self.data_liquidacao or self.valor_liquidado:
            erros["status"] = "Datas e valores de liquidação exigem status liquidado."
        if erros:
            raise ValidationError(erros)

    def __str__(self):
        return self.descricao

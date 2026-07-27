from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class AtivoMercado(models.TextChoices):
    SOJA_CBOT = "soja_cbot", "Soja CBOT"
    MILHO_CBOT = "milho_cbot", "Milho CBOT"
    TRIGO_CBOT = "trigo_cbot", "Trigo CBOT"
    FARELO_SOJA = "farelo_soja", "Farelo de soja"
    OLEO_SOJA = "oleo_soja", "Óleo de soja"
    BRENT = "brent", "Petróleo Brent"
    DOLAR = "dolar", "Dólar PTAX"


class CotacaoAtivoMercado(models.Model):
    class Intervalo(models.TextChoices):
        SNAPSHOT = "snapshot", "Snapshot"
        DIARIO = "diario", "Diário"

    ativo = models.CharField(max_length=24, choices=AtivoMercado.choices)
    intervalo = models.CharField(max_length=12, choices=Intervalo.choices)
    data_hora = models.DateTimeField()
    abertura = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    maxima = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    minima = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    fechamento = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        validators=[MinValueValidator(Decimal("0"))],
    )
    volume = models.DecimalField(max_digits=22, decimal_places=3, null=True, blank=True)
    unidade = models.CharField(max_length=60)
    moeda = models.CharField(max_length=12, default="USD")
    fonte = models.CharField(max_length=80)
    simbolo_origem = models.CharField(max_length=40, blank=True)
    recebido_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("ativo", "data_hora")
        constraints = [
            models.UniqueConstraint(
                fields=("ativo", "intervalo", "data_hora"),
                name="mercado_enterprise_ativo_intervalo_data_unico",
            ),
            models.CheckConstraint(
                condition=models.Q(fechamento__gte=0),
                name="mercado_enterprise_fechamento_nao_negativo",
            ),
        ]
        indexes = [
            models.Index(
                fields=("ativo", "intervalo", "-data_hora"),
                name="merc_ent_ativo_int_data_idx",
            ),
        ]

    def __str__(self):
        return f"{self.get_ativo_display()} - {self.data_hora:%d/%m/%Y %H:%M}"


class ConfiguracaoAtivoMercado(models.Model):
    class Status(models.TextChoices):
        PENDENTE = "pendente", "Pendente"
        ATUALIZADO = "atualizado", "Atualizado"
        ERRO = "erro", "Erro"
        DESATUALIZADO = "desatualizado", "Desatualizado"
        DESATIVADO = "desativado", "Desativado"

    ativo = models.CharField(max_length=24, choices=AtivoMercado.choices, unique=True)
    habilitado = models.BooleanField(default=True)
    provedor = models.CharField(max_length=40, default="stooq")
    simbolo = models.CharField(max_length=40)
    frequencia_minutos = models.PositiveIntegerField(default=15)
    ultima_tentativa = models.DateTimeField(null=True, blank=True)
    ultima_atualizacao = models.DateTimeField(null=True, blank=True)
    proxima_atualizacao = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDENTE)
    mensagem_erro = models.CharField(max_length=240, blank=True)
    falhas_consecutivas = models.PositiveIntegerField(default=0)
    total_chamadas = models.PositiveBigIntegerField(default=0)
    total_atualizacoes = models.PositiveBigIntegerField(default=0)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("ativo",)

    def __str__(self):
        return self.get_ativo_display()


class AtualizacaoMercado(models.Model):
    class Status(models.TextChoices):
        SUCESSO = "sucesso", "Sucesso"
        ERRO = "erro", "Erro"
        CACHE = "cache", "Cache"
        IGNORADA = "ignorada", "Ignorada"

    ativo = models.CharField(max_length=24, choices=AtivoMercado.choices)
    status = models.CharField(max_length=12, choices=Status.choices)
    iniciada_em = models.DateTimeField()
    finalizada_em = models.DateTimeField()
    provedor = models.CharField(max_length=40)
    chamadas_realizadas = models.PositiveSmallIntegerField(default=0)
    pontos_snapshot = models.PositiveIntegerField(default=0)
    pontos_diarios = models.PositiveIntegerField(default=0)
    utilizou_cache = models.BooleanField(default=False)
    tipo_erro = models.CharField(max_length=80, blank=True)
    mensagem_erro = models.CharField(max_length=240, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-iniciada_em", "-id")
        indexes = [
            models.Index(fields=("ativo", "-iniciada_em"), name="merc_atual_ativo_data_idx"),
        ]

    def __str__(self):
        return f"{self.get_ativo_display()} - {self.status}"

from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


ZERO = Decimal("0.000")


class VendaGraos(models.Model):
    class Status(models.TextChoices):
        RASCUNHO = "rascunho", "Rascunho"
        CONFIRMADA = "confirmada", "Confirmada"
        PARCIAL = "parcial", "Parcialmente entregue"
        ENTREGUE = "entregue", "Entregue"
        CANCELADA = "cancelada", "Cancelada"

    numero_contrato = models.CharField(max_length=80, unique=True)
    cliente_nome = models.CharField(max_length=160)
    posicao = models.ForeignKey(
        "graos.PosicaoSaldoGraos",
        on_delete=models.PROTECT,
        related_name="vendas",
    )
    lote = models.ForeignKey(
        "graos.LoteGraos",
        on_delete=models.PROTECT,
        related_name="vendas",
    )
    quantidade_kg = models.DecimalField(
        max_digits=16,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
    )
    quantidade_entregue_kg = models.DecimalField(
        max_digits=16, decimal_places=3, default=ZERO
    )
    quantidade_devolvida_kg = models.DecimalField(
        max_digits=16, decimal_places=3, default=ZERO
    )
    quantidade_cancelada_kg = models.DecimalField(
        max_digits=16, decimal_places=3, default=ZERO
    )
    data_contrato = models.DateField(default=timezone.localdate)
    data_limite_entrega = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.RASCUNHO
    )
    reserva = models.OneToOneField(
        "graos.ReservaSaldoGraos",
        on_delete=models.PROTECT,
        related_name="venda",
        null=True,
        blank=True,
    )
    observacoes = models.TextField(blank=True)
    chave_criacao = models.CharField(max_length=120, unique=True)
    hash_criacao = models.CharField(max_length=64)
    chave_confirmacao = models.CharField(
        max_length=120, unique=True, null=True, blank=True
    )
    hash_confirmacao = models.CharField(max_length=64, blank=True)
    chave_cancelamento = models.CharField(
        max_length=120, unique=True, null=True, blank=True
    )
    hash_cancelamento = models.CharField(max_length=64, blank=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="vendas_graos_criadas",
    )
    confirmado_em = models.DateTimeField(null=True, blank=True)
    cancelado_em = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-data_contrato", "-id")
        indexes = [
            models.Index(
                fields=("status", "data_contrato"), name="vendas_status_data_idx"
            ),
            models.Index(
                fields=("posicao", "status"), name="vendas_posicao_status_idx"
            ),
            models.Index(fields=("cliente_nome",), name="vendas_cliente_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantidade_kg__gt=0),
                name="vendas_quantidade_positiva",
            ),
            models.CheckConstraint(
                condition=models.Q(quantidade_entregue_kg__gte=0),
                name="vendas_entregue_nao_negativa",
            ),
            models.CheckConstraint(
                condition=models.Q(quantidade_devolvida_kg__gte=0),
                name="vendas_devolvida_nao_negativa",
            ),
            models.CheckConstraint(
                condition=models.Q(quantidade_cancelada_kg__gte=0),
                name="vendas_cancelada_nao_negativa",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    quantidade_entregue_kg__lte=models.F("quantidade_kg")
                ),
                name="vendas_entregue_ate_contratada",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    quantidade_devolvida_kg__lte=models.F("quantidade_entregue_kg")
                ),
                name="vendas_devolvida_ate_entregue",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    quantidade_cancelada_kg__lte=models.F("quantidade_kg")
                ),
                name="vendas_cancelada_ate_contratada",
            ),
        ]

    @property
    def quantidade_reservada_kg(self):
        if not self.reserva_id:
            return ZERO
        return self.reserva.saldo_reservado_kg

    @property
    def quantidade_aberta_kg(self):
        return max(
            ZERO,
            self.quantidade_kg
            - self.quantidade_entregue_kg
            - self.quantidade_cancelada_kg,
        )

    def __str__(self):
        return f"{self.numero_contrato} - {self.cliente_nome}"


class EntregaVendaGraos(models.Model):
    venda = models.ForeignKey(
        VendaGraos, on_delete=models.PROTECT, related_name="entregas"
    )
    quantidade_kg = models.DecimalField(max_digits=16, decimal_places=3)
    data_entrega = models.DateField(default=timezone.localdate)
    referencia_externa = models.CharField(max_length=120, blank=True)
    observacoes = models.TextField(blank=True)
    chave_idempotencia = models.CharField(max_length=120, unique=True)
    hash_requisicao = models.CharField(max_length=64)
    origem = models.OneToOneField(
        "graos.OrigemSaldoGraos",
        on_delete=models.PROTECT,
        related_name="entrega_venda",
    )
    movimentacao = models.OneToOneField(
        "graos.MovimentacaoGraos",
        on_delete=models.PROTECT,
        related_name="entrega_venda",
    )
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="entregas_vendas_graos",
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-data_entrega", "-id")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantidade_kg__gt=0),
                name="vendas_entrega_quantidade_positiva",
            )
        ]


class DevolucaoVendaGraos(models.Model):
    venda = models.ForeignKey(
        VendaGraos, on_delete=models.PROTECT, related_name="devolucoes"
    )
    quantidade_kg = models.DecimalField(max_digits=16, decimal_places=3)
    data_devolucao = models.DateField(default=timezone.localdate)
    referencia_externa = models.CharField(max_length=120, blank=True)
    observacoes = models.TextField(blank=True)
    chave_idempotencia = models.CharField(max_length=120, unique=True)
    hash_requisicao = models.CharField(max_length=64)
    origem = models.OneToOneField(
        "graos.OrigemSaldoGraos",
        on_delete=models.PROTECT,
        related_name="devolucao_venda",
    )
    movimentacao = models.OneToOneField(
        "graos.MovimentacaoGraos",
        on_delete=models.PROTECT,
        related_name="devolucao_venda",
    )
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="devolucoes_vendas_graos",
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-data_devolucao", "-id")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantidade_kg__gt=0),
                name="vendas_devolucao_quantidade_positiva",
            )
        ]


from decimal import Decimal
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.propriedades.models import Propriedade


class ProdutoEstoque(models.Model):
    class Categoria(models.TextChoices):
        INSUMO = "insumo", "Insumo"
        HERBICIDA = "herbicida", "Herbicida"
        FUNGICIDA = "fungicida", "Fungicida"
        FERTILIZANTE = "fertilizante", "Fertilizante"
        SEMENTE = "semente", "Semente"
        OUTRO = "outro", "Outro"

    class Unidade(models.TextChoices):
        KG = "kg", "Quilograma"
        L = "l", "Litro"
        UN = "un", "Unidade"
        SC = "sc", "Saca"
        TON = "t", "Tonelada"

    nome = models.CharField(max_length=160)
    categoria = models.CharField(max_length=20, choices=Categoria.choices)
    unidade = models.CharField(max_length=5, choices=Unidade.choices)
    fabricante = models.CharField(max_length=120, blank=True)
    estoque_minimo = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("nome",)
        constraints = [
            models.UniqueConstraint(
                fields=("nome", "fabricante"),
                name="estoque_produto_nome_fabricante_unico",
            ),
        ]

    def __str__(self):
        return self.nome


class LocalEstoque(models.Model):
    nome = models.CharField(max_length=120)
    propriedade = models.ForeignKey(
        Propriedade,
        on_delete=models.PROTECT,
        related_name="locais_estoque",
        null=True,
        blank=True,
    )
    descricao = models.CharField(max_length=240, blank=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("nome",)
        constraints = [
            models.UniqueConstraint(
                fields=("nome", "propriedade"),
                name="estoque_local_nome_propriedade_unico",
            ),
        ]

    def __str__(self):
        return self.nome


class LoteEstoque(models.Model):
    produto = models.ForeignKey(
        ProdutoEstoque,
        on_delete=models.PROTECT,
        related_name="lotes",
    )
    local = models.ForeignKey(
        LocalEstoque,
        on_delete=models.PROTECT,
        related_name="lotes",
        null=True,
        blank=True,
    )
    fornecedor = models.ForeignKey(
        "financeiro.ParceiroFinanceiro",
        on_delete=models.PROTECT,
        related_name="lotes_estoque",
        null=True,
        blank=True,
    )
    codigo = models.CharField(max_length=100)
    data_validade = models.DateField(null=True, blank=True)
    observacoes = models.CharField(max_length=240, blank=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("data_validade", "codigo")
        constraints = [
            models.UniqueConstraint(
                fields=("produto", "local", "codigo"),
                name="estoque_lote_produto_local_codigo_unico",
            ),
            models.UniqueConstraint(
                fields=("produto", "fornecedor", "codigo"),
                condition=models.Q(local__isnull=True),
                name="estoque_lote_prod_forn_codigo_unico",
            ),
        ]

    @property
    def vencido(self):
        return bool(self.data_validade and self.data_validade < timezone.localdate())

    def __str__(self):
        return f"{self.produto} - {self.codigo}"


class MovimentacaoEstoque(models.Model):
    class Tipo(models.TextChoices):
        ENTRADA = "entrada", "Entrada"
        SAIDA = "saida", "Saída"

    tipo = models.CharField(max_length=8, choices=Tipo.choices)
    lote = models.ForeignKey(
        LoteEstoque,
        on_delete=models.PROTECT,
        related_name="movimentacoes",
    )
    quantidade = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
    )
    custo_unitario = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    data_movimento = models.DateField(default=timezone.localdate)
    documento_fiscal = models.CharField(max_length=80, blank=True)
    propriedade = models.ForeignKey(
        Propriedade,
        on_delete=models.PROTECT,
        related_name="movimentacoes_estoque",
        null=True,
        blank=True,
    )
    safra = models.CharField(max_length=20, blank=True)
    observacoes = models.TextField(blank=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="movimentacoes_estoque",
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-data_movimento", "-id")
        indexes = [
            models.Index(
                fields=("lote", "data_movimento"),
                name="estoque_lote_data_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantidade__gt=0),
                name="estoque_movimento_quantidade_positiva",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(custo_unitario__isnull=True)
                    | models.Q(custo_unitario__gte=0)
                ),
                name="estoque_movimento_custo_nao_negativo",
            ),
        ]

    def clean(self):
        if self.tipo == self.Tipo.ENTRADA and self.custo_unitario is None:
            raise ValidationError(
                {"custo_unitario": "Informe o custo unitário da entrada."}
            )

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.lote}"


class CompraEstoque(models.Model):
    """Dados da compra em embalagens, ligados à entrada na unidade do produto."""

    id = models.UUIDField(primary_key=True, editable=False)
    assinatura = models.CharField(max_length=64, editable=False)
    movimento = models.OneToOneField(MovimentacaoEstoque, on_delete=models.PROTECT, related_name="compra")
    cultura = models.CharField(max_length=100, blank=True)
    quantidade_embalagens = models.DecimalField(max_digits=14, decimal_places=3, validators=[MinValueValidator(Decimal("0.001"))])
    embalagem = models.CharField(max_length=20)
    conteudo_embalagem = models.DecimalField(max_digits=14, decimal_places=3, validators=[MinValueValidator(Decimal("0.001"))])
    custo_embalagem = models.DecimalField(max_digits=14, decimal_places=4, validators=[MinValueValidator(Decimal("0"))])
    data_vencimento = models.DateField(null=True, blank=True)
    valor_total = models.DecimalField(max_digits=24, decimal_places=2)
    data_pagamento = models.DateField(null=True, blank=True)
    valor_pago = models.DecimalField(max_digits=24, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal("0"))])

    class Meta:
        ordering = ("-movimento__data_movimento", "-movimento_id")
        constraints = [
            models.CheckConstraint(condition=models.Q(quantidade_embalagens__gt=0, conteudo_embalagem__gt=0, custo_embalagem__gte=0, valor_total__gte=0), name="estoque_compra_valores_validos"),
            models.CheckConstraint(
                condition=(models.Q(data_pagamento__isnull=True, valor_pago__isnull=True) | models.Q(data_pagamento__isnull=False, valor_pago__isnull=False, valor_pago__gte=0)),
                name="estoque_compra_pagamento_valido",
            ),
        ]


class FaturamentoInsumo(models.Model):
    """Snapshot confirmado, preservado para auditoria mesmo após exclusão."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assinatura = models.CharField(max_length=64)
    fornecedor = models.ForeignKey("financeiro.ParceiroFinanceiro", on_delete=models.PROTECT)
    produto = models.ForeignKey(ProdutoEstoque, on_delete=models.PROTECT)
    data_envio = models.DateField()
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    criado_em = models.DateTimeField(auto_now_add=True)
    resumo = models.JSONField()
    excluido_em = models.DateTimeField(null=True, blank=True, editable=False)
    excluido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="faturamentos_insumos_excluidos", editable=False,
    )

    class Meta:
        ordering = ("-criado_em",)


class BaixaFaturamentoInsumo(models.Model):
    faturamento = models.ForeignKey(FaturamentoInsumo, on_delete=models.PROTECT, related_name="baixas")
    movimento = models.OneToOneField(MovimentacaoEstoque, on_delete=models.PROTECT, related_name="baixa_faturamento")

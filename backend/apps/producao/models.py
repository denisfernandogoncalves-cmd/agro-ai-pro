from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from apps.estoque.models import LoteEstoque, MovimentacaoEstoque
from apps.talhoes.models import Talhao


class OperacaoAgricola(models.Model):
    class Tipo(models.TextChoices):
        PREPARO = "preparo", "Preparo do solo"
        PLANTIO = "plantio", "Plantio"
        ADUBACAO = "adubacao", "Adubação"
        PULVERIZACAO = "pulverizacao", "Pulverização"
        IRRIGACAO = "irrigacao", "Irrigação"
        COLHEITA = "colheita", "Colheita"
        OUTRA = "outra", "Outra"

    class Status(models.TextChoices):
        PLANEJADA = "planejada", "Planejada"
        EM_EXECUCAO = "em_execucao", "Em execução"
        CONCLUIDA = "concluida", "Concluída"
        CANCELADA = "cancelada", "Cancelada"

    talhao = models.ForeignKey(
        Talhao,
        on_delete=models.PROTECT,
        related_name="operacoes",
    )
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    descricao = models.CharField(max_length=220)
    data_planejada = models.DateField()
    data_inicio = models.DateField(null=True, blank=True)
    data_conclusao = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.PLANEJADA,
    )
    area_hectares = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    responsavel = models.CharField(max_length=120, blank=True)
    custo_estimado = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    custo_realizado = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    observacoes = models.TextField(blank=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="operacoes_agricolas",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("data_planejada", "id")
        indexes = [
            models.Index(
                fields=("status", "data_planejada"),
                name="producao_status_data_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(area_hectares__gt=0),
                name="producao_operacao_area_positiva",
            ),
            models.CheckConstraint(
                condition=models.Q(custo_estimado__gte=0),
                name="producao_custo_estimado_nao_negativo",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(custo_realizado__isnull=True)
                    | models.Q(custo_realizado__gte=0)
                ),
                name="producao_custo_realizado_nao_negativo",
            ),
        ]

    def clean(self):
        erros = {}
        if (
            self.talhao_id
            and self.area_hectares is not None
            and Decimal(str(self.area_hectares))
            > Decimal(str(self.talhao.area_hectares))
        ):
            erros["area_hectares"] = "A área da operação não pode superar a área do talhão."
        if self.data_inicio and self.data_inicio < self.data_planejada:
            erros["data_inicio"] = "O início não pode ser anterior à data planejada."
        if self.data_conclusao and (
            not self.data_inicio or self.data_conclusao < self.data_inicio
        ):
            erros["data_conclusao"] = "A conclusão exige início na mesma data ou antes."
        if erros:
            raise ValidationError(erros)

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.talhao}"


class InsumoOperacao(models.Model):
    operacao = models.ForeignKey(
        OperacaoAgricola,
        on_delete=models.CASCADE,
        related_name="insumos",
    )
    lote = models.ForeignKey(
        LoteEstoque,
        on_delete=models.PROTECT,
        related_name="usos_em_operacoes",
    )
    quantidade_planejada = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
    )
    quantidade_utilizada = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.001"))],
    )
    movimentacao_estoque = models.OneToOneField(
        MovimentacaoEstoque,
        on_delete=models.PROTECT,
        related_name="insumo_operacao",
        null=True,
        blank=True,
        editable=False,
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("lote__produto__nome", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("operacao", "lote"),
                name="producao_operacao_lote_unico",
            ),
        ]

    def clean(self):
        erros = {}
        if self.operacao_id and self.operacao.status not in {
            OperacaoAgricola.Status.PLANEJADA,
            OperacaoAgricola.Status.EM_EXECUCAO,
        }:
            erros["operacao"] = "Os insumos não podem ser alterados após o encerramento."
        if self.quantidade_utilizada and self.quantidade_utilizada <= 0:
            erros["quantidade_utilizada"] = "A quantidade utilizada deve ser positiva."
        if erros:
            raise ValidationError(erros)

    def __str__(self):
        return f"{self.lote.produto} em {self.operacao}"


from .grain_models import (  # noqa: E402,F401
    AcessoCadPro,
    AuditoriaProducao,
    CadPro,
    ContratoProducao,
    Cultura,
    EmbarqueProducao,
    ImportacaoPlanilha,
    Motorista,
    MovimentacaoGraos,
    RecebimentoProducao,
    Safra,
    SaldoGraos,
    Veiculo,
)
from .joint_models import (  # noqa: E402,F401
    CadProLoteConjunto,
    CargaLoteConjunto,
    LoteConjuntoProducao,
    MovimentacaoLoteConjunto,
    ParticipanteLoteConjunto,
    SaidaLoteConjunto,
    SaldoLoteConjunto,
    TalhaoParticipanteLoteConjunto,
)

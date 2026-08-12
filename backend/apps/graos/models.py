import re
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.utils import timezone

from apps.propriedades.models import Propriedade
from apps.talhoes.models import Talhao


ZERO = Decimal("0.000")


def normalizar_placa(placa):
    return re.sub(r"[^A-Z0-9]", "", str(placa or "").upper())


class MovimentacaoGraosQuerySet(models.QuerySet):
    """Impede que o ledger seja reescrito ou apagado por atalhos do ORM."""

    def update(self, **kwargs):
        raise ValidationError("Movimentações de grãos são imutáveis.")

    def delete(self):
        raise ValidationError("Movimentações de grãos são imutáveis.")

    def bulk_update(self, objs, fields, batch_size=None):
        raise ValidationError("Movimentações de grãos são imutáveis.")


class MovimentacaoGraosManager(
    models.Manager.from_queryset(MovimentacaoGraosQuerySet)
):
    pass


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
    cad_pro = models.ForeignKey(
        "cadpro.CADPro",
        on_delete=models.PROTECT,
        related_name="lotes_graos",
        null=True,
        blank=True,
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
    classificacao_codigo = models.CharField(max_length=50, default="PADRAO")
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
            models.Index(
                fields=("cad_pro", "cultura", "safra", "classificacao_codigo"),
                name="graos_lote_posicao_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=("armazem", "codigo"),
                name="graos_lote_codigo_armazem_unico",
            ),
            models.CheckConstraint(
                condition=~models.Q(classificacao_codigo=""),
                name="graos_lote_classificacao_preenchida",
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
        self.cultura = " ".join(str(self.cultura or "").strip().split())
        self.safra = " ".join(str(self.safra or "").strip().split())
        self.classificacao_codigo = str(
            self.classificacao_codigo or ""
        ).strip().upper()
        erros = {}
        if not self.classificacao_codigo:
            erros["classificacao_codigo"] = "Informe a classificação dos grãos."
        if (
            self.talhao_id
            and self.armazem_id
            and self.talhao.propriedade_id != self.armazem.propriedade_id
        ):
            erros["talhao"] = (
                "O talhão e o armazém devem pertencer à mesma propriedade."
            )
        if self.cad_pro_id and self.armazem_id:
            from apps.cadpro.models import CADProPropriedade

            if not CADProPropriedade.objects.filter(
                cad_pro_id=self.cad_pro_id,
                propriedade_id=self.armazem.propriedade_id,
                ativo=True,
                cad_pro__ativo=True,
            ).exists():
                erros["cad_pro"] = (
                    "O CAD/PRO deve possuir vínculo ativo com a propriedade do armazém."
                )
        if erros:
            raise ValidationError(erros)

    def __str__(self):
        return f"{self.codigo} - {self.cultura} ({self.safra})"


class GrupoColheita(models.Model):
    propriedade = models.ForeignKey(
        Propriedade,
        on_delete=models.PROTECT,
        related_name="grupos_colheita",
    )
    cad_pro = models.ForeignKey(
        "cadpro.CADPro",
        on_delete=models.PROTECT,
        related_name="grupos_colheita",
    )
    armazem_padrao = models.ForeignKey(
        ArmazemGraos,
        on_delete=models.PROTECT,
        related_name="grupos_colheita_padrao",
        null=True,
    )
    nome = models.CharField(max_length=120)
    cultura = models.CharField(max_length=50)
    safra = models.CharField(max_length=20)
    observacoes = models.TextField(blank=True)
    tolerancia_umidade_percentual = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("100.00"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
    )
    desconto_umidade_por_ponto = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        default=ZERO,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
    )
    tolerancia_impureza_percentual = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("100.00"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
    )
    desconto_impureza_por_ponto = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        default=ZERO,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
    )
    tolerancia_defeitos_percentual = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("100.00"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
    )
    desconto_defeitos_por_ponto = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        default=ZERO,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
    )
    ativo = models.BooleanField(default=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="grupos_colheita_criados",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-safra", "cultura", "nome", "id")
        verbose_name = "grupo de colheita"
        verbose_name_plural = "grupos de colheita"
        constraints = [
            models.UniqueConstraint(
                fields=("propriedade", "cad_pro", "nome", "cultura", "safra"),
                name="graos_grupo_colheita_unico",
            ),
        ]
        indexes = [
            models.Index(
                fields=("propriedade", "safra", "cultura"),
                name="graos_grupo_prop_safra_idx",
            ),
        ]

    def clean(self):
        super().clean()
        self.nome = " ".join(str(self.nome or "").strip().split())
        self.cultura = " ".join(str(self.cultura or "").strip().split()).title()
        self.safra = " ".join(str(self.safra or "").strip().split())
        erros = {}
        if not self.nome:
            erros["nome"] = "Informe o nome do grupo de colheita."
        if not self.cultura:
            erros["cultura"] = "Informe a cultura."
        if not self.safra:
            erros["safra"] = "Informe a safra."
        if self.cad_pro_id and self.propriedade_id:
            from apps.cadpro.models import CADProPropriedade

            if not CADProPropriedade.objects.filter(
                cad_pro_id=self.cad_pro_id,
                propriedade_id=self.propriedade_id,
                ativo=True,
                cad_pro__ativo=True,
            ).exists():
                erros["cad_pro"] = "O CAD/PRO deve possuir vínculo ativo com a propriedade."
        if self.armazem_padrao_id and self.propriedade_id:
            if self.armazem_padrao.propriedade_id != self.propriedade_id:
                erros["armazem_padrao"] = (
                    "A armazenagem padrão deve pertencer à propriedade do grupo."
                )
            elif not self.armazem_padrao.ativo:
                erros["armazem_padrao"] = "A armazenagem padrão deve estar ativa."
        if self.pk and CargaColhida.objects.filter(grupo_colheita_id=self.pk).exists():
            original = getattr(self, "_original_bloqueado", None)
            if original is None:
                original = GrupoColheita.objects.get(pk=self.pk)
            campos_estruturais = (
                "propriedade_id",
                "cad_pro_id",
                "cultura",
                "safra",
                "armazem_padrao_id",
            )
            if any(
                getattr(self, campo) != getattr(original, campo)
                for campo in campos_estruturais
            ):
                erros["detail"] = (
                    "O contexto estrutural do grupo não pode mudar após a "
                    "primeira carga vinculada."
                )
        if erros:
            raise ValidationError(erros)

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.full_clean()
            return super().save(*args, **kwargs)
        with transaction.atomic():
            self._original_bloqueado = (
                GrupoColheita.objects.select_for_update().get(pk=self.pk)
            )
            try:
                self.full_clean()
                return super().save(*args, **kwargs)
            finally:
                del self._original_bloqueado

    def __str__(self):
        return f"{self.nome} - {self.cultura} ({self.safra})"


class CargaColhidaQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError("Cargas colhidas são imutáveis.")

    def delete(self):
        raise ValidationError("Cargas colhidas são imutáveis.")


class CargaColhida(models.Model):
    grupo_colheita = models.ForeignKey(
        GrupoColheita,
        on_delete=models.PROTECT,
        related_name="cargas",
    )
    armazem = models.ForeignKey(
        ArmazemGraos,
        on_delete=models.PROTECT,
        related_name="cargas_colhidas",
    )
    lote = models.ForeignKey(
        LoteGraos,
        on_delete=models.PROTECT,
        related_name="cargas_colhidas",
    )
    data_colheita = models.DateField(default=timezone.localdate)
    placa = models.CharField(max_length=7)
    peso_bruto_kg = models.DecimalField(
        max_digits=16,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
    )
    umidade_percentual = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
    )
    impureza_percentual = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
    )
    defeitos_percentual = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
    )
    ph = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
    )
    destinado_semente = models.BooleanField(default=False)
    local_colheita = models.CharField(max_length=160, blank=True)
    desconto_total_percentual = models.DecimalField(max_digits=7, decimal_places=3)
    desconto_total_kg = models.DecimalField(max_digits=16, decimal_places=3)
    peso_liquido_kg = models.DecimalField(max_digits=16, decimal_places=3)
    sacas_60kg = models.DecimalField(max_digits=16, decimal_places=3)
    regra_desconto_aplicada = models.JSONField(default=dict)
    fingerprint = models.CharField(max_length=64, unique=True, editable=False)
    movimentacao = models.OneToOneField(
        "MovimentacaoGraos",
        on_delete=models.PROTECT,
        related_name="carga_colhida",
        null=True,
        blank=True,
        editable=False,
    )
    observacoes = models.TextField(blank=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="cargas_colhidas_criadas",
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    objects = CargaColhidaQuerySet.as_manager()

    class Meta:
        ordering = ("-data_colheita", "-id")
        verbose_name = "carga colhida"
        verbose_name_plural = "cargas colhidas"
        indexes = [
            models.Index(
                fields=("grupo_colheita", "data_colheita"),
                name="graos_carga_grupo_data_idx",
            ),
            models.Index(fields=("placa", "data_colheita"), name="graos_carga_placa_data_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(peso_bruto_kg__gt=0),
                name="graos_carga_peso_bruto_positivo",
            ),
            models.CheckConstraint(
                condition=models.Q(peso_liquido_kg__gt=0),
                name="graos_carga_peso_liquido_positivo",
            ),
            models.CheckConstraint(
                condition=models.Q(peso_liquido_kg__lte=models.F("peso_bruto_kg")),
                name="graos_carga_liquido_ate_bruto",
            ),
        ]

    @property
    def propriedade_id(self):
        return self.grupo_colheita.propriedade_id

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Cargas colhidas são imutáveis.")
        self.placa = normalizar_placa(self.placa)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Cargas colhidas são imutáveis.")

    def __str__(self):
        return f"{self.data_colheita} - {self.placa} - {self.peso_liquido_kg} kg"


class PosicaoSaldoGraos(models.Model):
    cad_pro = models.ForeignKey(
        "cadpro.CADPro",
        on_delete=models.PROTECT,
        related_name="posicoes_saldo_graos",
    )
    cultura = models.CharField(max_length=50)
    safra = models.CharField(max_length=20)
    classificacao_codigo = models.CharField(max_length=50, default="PADRAO")
    armazem = models.ForeignKey(
        ArmazemGraos,
        on_delete=models.PROTECT,
        related_name="posicoes_saldo",
    )
    saldo_fisico_kg = models.DecimalField(
        max_digits=16,
        decimal_places=3,
        default=ZERO,
    )
    saldo_comprometido_kg = models.DecimalField(
        max_digits=16,
        decimal_places=3,
        default=ZERO,
    )
    versao = models.PositiveBigIntegerField(default=0)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("safra", "cultura", "classificacao_codigo", "armazem_id")
        verbose_name = "posição de saldo de grãos"
        verbose_name_plural = "posições de saldo de grãos"
        constraints = [
            models.UniqueConstraint(
                fields=(
                    "cad_pro",
                    "cultura",
                    "safra",
                    "classificacao_codigo",
                    "armazem",
                ),
                name="graos_posicao_chave_unica",
            ),
            models.CheckConstraint(
                condition=models.Q(saldo_fisico_kg__gte=0),
                name="graos_posicao_fisico_nao_negativo",
            ),
            models.CheckConstraint(
                condition=models.Q(saldo_comprometido_kg__gte=0),
                name="graos_posicao_comprom_nao_negativo",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    saldo_comprometido_kg__lte=models.F("saldo_fisico_kg")
                ),
                name="graos_posicao_comprom_ate_fisico",
            ),
        ]
        indexes = [
            models.Index(
                fields=("cad_pro", "cultura", "safra"),
                name="graos_posicao_cad_cult_idx",
            ),
            models.Index(
                fields=("armazem", "classificacao_codigo"),
                name="graos_posicao_arm_class_idx",
            ),
        ]

    @property
    def saldo_disponivel_kg(self):
        return self.saldo_fisico_kg - self.saldo_comprometido_kg

    def __str__(self):
        return (
            f"{self.cad_pro} - {self.cultura} {self.safra} "
            f"{self.classificacao_codigo} - {self.armazem}"
        )


class OrigemSaldoGraos(models.Model):
    class Tipo(models.TextChoices):
        PRODUCAO = "producao", "Produção"
        RESERVA = "reserva", "Reserva"
        LIBERACAO = "liberacao", "Liberação de reserva"
        ENTREGA = "entrega", "Entrega"
        DEVOLUCAO = "devolucao", "Devolução"
        AJUSTE = "ajuste", "Ajuste"
        ESTORNO = "estorno", "Estorno"
        TRANSFERENCIA = "transferencia", "Transferência"
        RECONCILIACAO = "reconciliacao", "Reconciliação"
        LEGADO = "legado", "Legado"

    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    chave_idempotencia = models.CharField(max_length=160, unique=True)
    referencia_externa = models.CharField(max_length=160, blank=True)
    hash_requisicao = models.CharField(max_length=64)
    metadados = models.JSONField(default=dict, blank=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="origens_saldo_graos",
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-criado_em", "-id")
        verbose_name = "origem de saldo de grãos"
        verbose_name_plural = "origens de saldo de grãos"
        indexes = [
            models.Index(
                fields=("tipo", "referencia_externa"),
                name="graos_origem_tipo_ref_idx",
            ),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.chave_idempotencia}"


class ReservaSaldoGraos(models.Model):
    class Status(models.TextChoices):
        ATIVA = "ativa", "Ativa"
        PARCIAL = "parcial", "Parcialmente atendida"
        CONCLUIDA = "concluida", "Concluída"
        LIBERADA = "liberada", "Liberada"

    posicao = models.ForeignKey(
        PosicaoSaldoGraos,
        on_delete=models.PROTECT,
        related_name="reservas",
    )
    origem = models.OneToOneField(
        OrigemSaldoGraos,
        on_delete=models.PROTECT,
        related_name="reserva_criada",
    )
    quantidade_kg = models.DecimalField(max_digits=16, decimal_places=3)
    saldo_reservado_kg = models.DecimalField(max_digits=16, decimal_places=3)
    referencia_externa = models.CharField(max_length=160, blank=True)
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.ATIVA,
    )
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reservas_saldo_graos",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-criado_em", "-id")
        verbose_name = "reserva de saldo de grãos"
        verbose_name_plural = "reservas de saldo de grãos"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantidade_kg__gt=0),
                name="graos_reserva_quantidade_positiva",
            ),
            models.CheckConstraint(
                condition=models.Q(saldo_reservado_kg__gte=0),
                name="graos_reserva_saldo_nao_negativo",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    saldo_reservado_kg__lte=models.F("quantidade_kg")
                ),
                name="graos_reserva_saldo_ate_quantidade",
            ),
        ]

    def __str__(self):
        return f"Reserva {self.pk} - {self.saldo_reservado_kg} kg"


class MovimentacaoGraos(models.Model):
    class Tipo(models.TextChoices):
        ENTRADA = "entrada", "Entrada"
        SAIDA = "saida", "Saída"

    class Operacao(models.TextChoices):
        CREDITO_PRODUCAO = "credito_producao", "Crédito de produção"
        RESERVA = "reserva", "Reserva"
        LIBERACAO = "liberacao", "Liberação"
        ENTREGA = "entrega", "Entrega"
        DEVOLUCAO = "devolucao", "Devolução"
        AJUSTE = "ajuste", "Ajuste"
        ESTORNO = "estorno", "Estorno"
        TRANSFERENCIA_SAIDA = "transferencia_saida", "Transferência - saída"
        TRANSFERENCIA_ENTRADA = "transferencia_entrada", "Transferência - entrada"
        LEGADO = "legado", "Legado"

    tipo = models.CharField(max_length=8, choices=Tipo.choices)
    operacao = models.CharField(max_length=24, choices=Operacao.choices)
    lote = models.ForeignKey(
        LoteGraos,
        on_delete=models.PROTECT,
        related_name="movimentacoes",
    )
    posicao = models.ForeignKey(
        PosicaoSaldoGraos,
        on_delete=models.PROTECT,
        related_name="movimentacoes",
    )
    origem = models.ForeignKey(
        OrigemSaldoGraos,
        on_delete=models.PROTECT,
        related_name="movimentacoes",
    )
    reserva = models.ForeignKey(
        ReservaSaldoGraos,
        on_delete=models.PROTECT,
        related_name="movimentacoes",
        null=True,
        blank=True,
    )
    estorno_de = models.OneToOneField(
        "self",
        on_delete=models.PROTECT,
        related_name="movimento_estorno",
        null=True,
        blank=True,
    )
    quantidade_kg = models.DecimalField(
        max_digits=16,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
    )
    delta_fisico_kg = models.DecimalField(
        max_digits=16,
        decimal_places=3,
        default=ZERO,
    )
    delta_comprometido_kg = models.DecimalField(
        max_digits=16,
        decimal_places=3,
        default=ZERO,
    )
    snapshot_anterior = models.JSONField(default=dict)
    snapshot_posterior = models.JSONField(default=dict)
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

    objects = MovimentacaoGraosManager()

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
            models.Index(
                fields=("posicao", "criado_em"),
                name="graos_mov_posicao_criado_idx",
            ),
            models.Index(
                fields=("origem", "operacao"),
                name="graos_mov_origem_oper_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantidade_kg__gt=0),
                name="graos_movimento_quantidade_positiva",
            ),
            models.CheckConstraint(
                condition=(
                    ~models.Q(delta_fisico_kg=0)
                    | ~models.Q(delta_comprometido_kg=0)
                ),
                name="graos_movimento_delta_nao_zero",
            ),
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Movimentações de grãos são imutáveis.")
        self.chave_idempotencia = self.chave_idempotencia or None
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Movimentações de grãos são imutáveis.")

    def __str__(self):
        return f"{self.get_operacao_display()} - {self.lote} - {self.quantidade_kg} kg"

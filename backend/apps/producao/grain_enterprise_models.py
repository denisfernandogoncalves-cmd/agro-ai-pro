from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from apps.estoque.models import LocalEstoque
from apps.financeiro.models import ParceiroFinanceiro
from apps.propriedades.models import Propriedade
from apps.talhoes.models import Talhao

from .grain_models import (
    AuditoriaProducao,
    CadPro,
    Cultura,
    EmbarqueProducao,
    MovimentacaoGraos,
    RecebimentoProducao,
    Safra,
)


class ConfiguracaoCultura(models.Model):
    cultura = models.OneToOneField(
        Cultura,
        on_delete=models.CASCADE,
        related_name="configuracao_producao",
    )
    umidade_alerta_percentual = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("14"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
    )
    estoque_minimo_kg = models.DecimalField(
        max_digits=18,
        decimal_places=3,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    observacoes = models.TextField(blank=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("cultura__nome",)

    def __str__(self):
        return f"Parâmetros de {self.cultura}"


class DetalheLocalArmazenagem(models.Model):
    class Tipo(models.TextChoices):
        SILO = "silo", "Silo"
        ARMAZEM = "armazem", "Armazém"
        COOPERATIVA = "cooperativa", "Cooperativa"
        TERCEIRO = "terceiro", "Armazém de terceiro"
        OUTRO = "outro", "Outro"

    local = models.OneToOneField(
        LocalEstoque,
        on_delete=models.CASCADE,
        related_name="detalhe_producao",
    )
    tipo = models.CharField(max_length=12, choices=Tipo.choices, default=Tipo.SILO)
    capacidade_kg = models.DecimalField(
        max_digits=18,
        decimal_places=3,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.001"))],
    )
    latitude = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("local__nome",)

    def clean(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValidationError("Latitude e longitude devem ser informadas em conjunto.")
        if self.local_id and self.local.propriedade_id is None and self.tipo != self.Tipo.TERCEIRO:
            raise ValidationError(
                {"tipo": "Locais globais devem ser identificados como armazenagem de terceiro."}
            )

    def __str__(self):
        return f"{self.local} - {self.get_tipo_display()}"


class OrigemTerceiroRecebimento(models.Model):
    recebimento = models.OneToOneField(
        RecebimentoProducao,
        on_delete=models.CASCADE,
        related_name="origem_terceiro",
    )
    terceiro = models.ForeignKey(
        ParceiroFinanceiro,
        on_delete=models.PROTECT,
        related_name="recebimentos_producao_terceiros",
    )
    documento_origem = models.CharField(max_length=80, blank=True)
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.terceiro_id and self.terceiro.tipo == ParceiroFinanceiro.Tipo.CLIENTE:
            raise ValidationError(
                {"terceiro": "O parceiro deve aceitar operações como fornecedor ou ambos."}
            )

    def __str__(self):
        return f"{self.terceiro} - recebimento {self.recebimento_id}"


class TransferenciaGraos(models.Model):
    class Status(models.TextChoices):
        RASCUNHO = "rascunho", "Rascunho"
        CONFIRMADA = "confirmada", "Confirmada"
        ESTORNADA = "estornada", "Estornada"

    data = models.DateTimeField(default=timezone.now)
    cultura = models.ForeignKey(Cultura, on_delete=models.PROTECT, related_name="transferencias")
    safra = models.ForeignKey(Safra, on_delete=models.PROTECT, related_name="transferencias")
    quantidade_kg = models.DecimalField(
        max_digits=18,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
    )
    propriedade_origem = models.ForeignKey(
        Propriedade,
        on_delete=models.PROTECT,
        related_name="transferencias_graos_enviadas",
    )
    cadpro_origem = models.ForeignKey(
        CadPro,
        on_delete=models.PROTECT,
        related_name="transferencias_enviadas",
    )
    talhao_origem = models.ForeignKey(
        Talhao,
        on_delete=models.PROTECT,
        related_name="transferencias_graos_enviadas",
        null=True,
        blank=True,
    )
    local_origem = models.ForeignKey(
        LocalEstoque,
        on_delete=models.PROTECT,
        related_name="transferencias_graos_enviadas",
    )
    propriedade_destino = models.ForeignKey(
        Propriedade,
        on_delete=models.PROTECT,
        related_name="transferencias_graos_recebidas",
    )
    cadpro_destino = models.ForeignKey(
        CadPro,
        on_delete=models.PROTECT,
        related_name="transferencias_recebidas",
    )
    talhao_destino = models.ForeignKey(
        Talhao,
        on_delete=models.PROTECT,
        related_name="transferencias_graos_recebidas",
        null=True,
        blank=True,
    )
    local_destino = models.ForeignKey(
        LocalEstoque,
        on_delete=models.PROTECT,
        related_name="transferencias_graos_recebidas",
    )
    movimento_saida = models.OneToOneField(
        MovimentacaoGraos,
        on_delete=models.PROTECT,
        related_name="transferencia_saida",
        null=True,
        blank=True,
        editable=False,
    )
    movimento_entrada = models.OneToOneField(
        MovimentacaoGraos,
        on_delete=models.PROTECT,
        related_name="transferencia_entrada",
        null=True,
        blank=True,
        editable=False,
    )
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.RASCUNHO)
    motivo = models.CharField(max_length=240, blank=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="transferencias_graos_criadas",
    )
    confirmado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="transferencias_graos_confirmadas",
        null=True,
        blank=True,
    )
    confirmado_em = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-data", "-id")
        indexes = [
            models.Index(
                fields=("propriedade_origem", "cadpro_origem", "data"),
                name="prod_transf_origem_idx",
            ),
            models.Index(
                fields=("propriedade_destino", "cadpro_destino", "data"),
                name="prod_transf_destino_idx",
            ),
        ]

    def clean(self):
        erros = {}
        if self.cadpro_origem_id and self.cadpro_origem.propriedade_id != self.propriedade_origem_id:
            erros["cadpro_origem"] = "O CAD/PRO de origem deve pertencer à propriedade de origem."
        if self.cadpro_destino_id and self.cadpro_destino.propriedade_id != self.propriedade_destino_id:
            erros["cadpro_destino"] = "O CAD/PRO de destino deve pertencer à propriedade de destino."
        if self.talhao_origem_id and self.talhao_origem.propriedade_id != self.propriedade_origem_id:
            erros["talhao_origem"] = "O talhão de origem deve pertencer à propriedade de origem."
        if self.talhao_destino_id and self.talhao_destino.propriedade_id != self.propriedade_destino_id:
            erros["talhao_destino"] = "O talhão de destino deve pertencer à propriedade de destino."
        if self.local_origem_id and self.local_origem.propriedade_id not in {None, self.propriedade_origem_id}:
            erros["local_origem"] = "O local de origem não pertence ao contexto informado."
        if self.local_destino_id and self.local_destino.propriedade_id not in {None, self.propriedade_destino_id}:
            erros["local_destino"] = "O local de destino não pertence ao contexto informado."
        origem = (
            self.propriedade_origem_id,
            self.cadpro_origem_id,
            self.talhao_origem_id,
            self.local_origem_id,
        )
        destino = (
            self.propriedade_destino_id,
            self.cadpro_destino_id,
            self.talhao_destino_id,
            self.local_destino_id,
        )
        if origem == destino:
            erros["local_destino"] = "Origem e destino da transferência devem ser diferentes."
        if erros:
            raise ValidationError(erros)

    def __str__(self):
        return f"Transferência {self.id or '-'} - {self.quantidade_kg} kg"


class NotaFiscalProducao(models.Model):
    class Tipo(models.TextChoices):
        PRODUTOR = "produtor", "Nota do produtor"
        EMPRESA = "empresa", "Nota da empresa"
        TERCEIRO = "terceiro", "Nota de terceiro"

    tipo = models.CharField(max_length=12, choices=Tipo.choices)
    propriedade = models.ForeignKey(
        Propriedade,
        on_delete=models.PROTECT,
        related_name="notas_fiscais_producao",
    )
    cadpro = models.ForeignKey(CadPro, on_delete=models.PROTECT, related_name="notas_fiscais")
    recebimento = models.ForeignKey(
        RecebimentoProducao,
        on_delete=models.PROTECT,
        related_name="notas_fiscais",
        null=True,
        blank=True,
    )
    embarque = models.ForeignKey(
        EmbarqueProducao,
        on_delete=models.PROTECT,
        related_name="notas_fiscais",
        null=True,
        blank=True,
    )
    numero = models.CharField(max_length=80)
    serie = models.CharField(max_length=20, blank=True)
    chave_acesso = models.CharField(max_length=44, unique=True, null=True, blank=True)
    data_emissao = models.DateField(default=timezone.localdate)
    valor = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    arquivo = models.FileField(upload_to="notas/producao/%Y/%m/", null=True, blank=True)
    observacoes = models.TextField(blank=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="notas_fiscais_producao",
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-data_emissao", "-id")
        constraints = [
            models.UniqueConstraint(
                fields=("propriedade", "tipo", "numero", "serie"),
                name="prod_nf_contexto_numero_unico",
            )
        ]

    def save(self, *args, **kwargs):
        self.chave_acesso = self.chave_acesso or None
        super().save(*args, **kwargs)

    def clean(self):
        erros = {}
        if self.cadpro_id and self.cadpro.propriedade_id != self.propriedade_id:
            erros["cadpro"] = "O CAD/PRO deve pertencer à propriedade."
        if bool(self.recebimento_id) == bool(self.embarque_id):
            erros["recebimento"] = "Vincule a nota a um recebimento ou a um embarque."
        referencia = self.recebimento or self.embarque
        if referencia and (
            referencia.propriedade_id != self.propriedade_id
            or referencia.cadpro_id != self.cadpro_id
        ):
            erros["cadpro"] = "A nota fiscal deve usar o mesmo contexto do documento vinculado."
        if self.chave_acesso and (len(self.chave_acesso) != 44 or not self.chave_acesso.isdigit()):
            erros["chave_acesso"] = "A chave de acesso deve conter 44 dígitos."
        if erros:
            raise ValidationError(erros)

    def __str__(self):
        return f"{self.get_tipo_display()} {self.numero}"


class AuditoriaCadPro(models.Model):
    auditoria = models.OneToOneField(
        AuditoriaProducao,
        on_delete=models.CASCADE,
        related_name="escopo_cadpro",
    )
    cadpro = models.ForeignKey(CadPro, on_delete=models.PROTECT, related_name="auditorias")

    class Meta:
        ordering = ("-auditoria__criado_em",)

    def __str__(self):
        return f"{self.cadpro} - auditoria {self.auditoria_id}"

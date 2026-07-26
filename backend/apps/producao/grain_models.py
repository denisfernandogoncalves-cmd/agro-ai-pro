from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from apps.estoque.models import LocalEstoque
from apps.financeiro.models import LancamentoFinanceiro, ParceiroFinanceiro
from apps.propriedades.models import Propriedade
from apps.talhoes.models import Talhao


PERCENTUAL_VALIDATORS = [MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))]


class Cultura(models.Model):
    nome = models.CharField(max_length=80, unique=True)
    codigo = models.SlugField(max_length=40, unique=True)
    peso_saca_kg = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        default=Decimal("60"),
        validators=[MinValueValidator(Decimal("0.001"))],
    )
    ativa = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("nome",)

    def __str__(self):
        return self.nome


class Safra(models.Model):
    nome = models.CharField(max_length=30, unique=True)
    data_inicio = models.DateField(null=True, blank=True)
    data_fim = models.DateField(null=True, blank=True)
    ativa = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-nome",)

    def clean(self):
        if self.data_inicio and self.data_fim and self.data_fim < self.data_inicio:
            raise ValidationError({"data_fim": "A data final não pode ser anterior à inicial."})

    def __str__(self):
        return self.nome


class CadPro(models.Model):
    propriedade = models.ForeignKey(
        Propriedade,
        on_delete=models.PROTECT,
        related_name="cadpros",
    )
    codigo = models.CharField(max_length=80)
    titular = models.CharField(max_length=160)
    documento = models.CharField(max_length=20, blank=True)
    inscricao_estadual = models.CharField(max_length=30, blank=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("propriedade__nome", "codigo")
        constraints = [
            models.UniqueConstraint(
                fields=("propriedade", "codigo"),
                name="producao_cadpro_codigo_propriedade_unico",
            )
        ]

    def __str__(self):
        return f"{self.codigo} - {self.propriedade}"


class AcessoCadPro(models.Model):
    cadpro = models.ForeignKey(CadPro, on_delete=models.CASCADE, related_name="acessos")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="acessos_cadpro",
    )
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("cadpro__propriedade__nome", "cadpro__codigo", "usuario__username")
        constraints = [
            models.UniqueConstraint(
                fields=("cadpro", "usuario"),
                name="producao_cadpro_usuario_unico",
            )
        ]
        indexes = [
            models.Index(fields=("usuario", "ativo"), name="producao_cadpro_usuario_idx")
        ]

    def __str__(self):
        return f"{self.usuario} - {self.cadpro}"


class Motorista(models.Model):
    nome = models.CharField(max_length=160)
    documento = models.CharField(max_length=20, blank=True, null=True, unique=True)
    telefone = models.CharField(max_length=30, blank=True)
    terceiro = models.ForeignKey(
        ParceiroFinanceiro,
        on_delete=models.PROTECT,
        related_name="motoristas_producao",
        null=True,
        blank=True,
    )
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("nome",)

    def save(self, *args, **kwargs):
        self.documento = self.documento or None
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nome


class Veiculo(models.Model):
    class Tipo(models.TextChoices):
        CAMINHAO = "caminhao", "Caminhão"
        CARRETA = "carreta", "Carreta"
        OUTRO = "outro", "Outro"

    placa = models.CharField(max_length=10, unique=True)
    tipo = models.CharField(max_length=12, choices=Tipo.choices, default=Tipo.CAMINHAO)
    descricao = models.CharField(max_length=120, blank=True)
    motorista_padrao = models.ForeignKey(
        Motorista,
        on_delete=models.PROTECT,
        related_name="veiculos",
        null=True,
        blank=True,
    )
    terceiro = models.ForeignKey(
        ParceiroFinanceiro,
        on_delete=models.PROTECT,
        related_name="veiculos_producao",
        null=True,
        blank=True,
    )
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("placa",)

    def save(self, *args, **kwargs):
        self.placa = self.placa.replace(" ", "").replace("-", "").upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.placa


class ContratoProducao(models.Model):
    class Status(models.TextChoices):
        ABERTO = "aberto", "Aberto"
        CONCLUIDO = "concluido", "Concluído"
        CANCELADO = "cancelado", "Cancelado"

    propriedade = models.ForeignKey(
        Propriedade,
        on_delete=models.PROTECT,
        related_name="contratos_producao",
    )
    cadpro = models.ForeignKey(CadPro, on_delete=models.PROTECT, related_name="contratos")
    cultura = models.ForeignKey(Cultura, on_delete=models.PROTECT, related_name="contratos")
    safra = models.ForeignKey(Safra, on_delete=models.PROTECT, related_name="contratos")
    comprador = models.ForeignKey(
        ParceiroFinanceiro,
        on_delete=models.PROTECT,
        related_name="contratos_producao",
    )
    numero = models.CharField(max_length=80)
    data_contrato = models.DateField(default=timezone.localdate)
    data_limite = models.DateField(null=True, blank=True)
    quantidade_kg = models.DecimalField(
        max_digits=16,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
    )
    preco_saca = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        validators=[MinValueValidator(Decimal("0.0001"))],
    )
    tolerancia_percentual = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        default=Decimal("0"),
        validators=PERCENTUAL_VALIDATORS,
    )
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ABERTO)
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-data_contrato", "numero")
        constraints = [
            models.UniqueConstraint(
                fields=("comprador", "numero"),
                name="producao_contrato_comprador_numero_unico",
            )
        ]

    def clean(self):
        erros = {}
        if self.cadpro_id and self.propriedade_id != self.cadpro.propriedade_id:
            erros["cadpro"] = "O CAD/PRO deve pertencer à propriedade informada."
        if self.data_limite and self.data_limite < self.data_contrato:
            erros["data_limite"] = "A data limite não pode ser anterior ao contrato."
        if erros:
            raise ValidationError(erros)

    def __str__(self):
        return f"{self.numero} - {self.comprador}"


class RecebimentoProducao(models.Model):
    class Status(models.TextChoices):
        RASCUNHO = "rascunho", "Rascunho"
        CONFIRMADO = "confirmado", "Confirmado"
        ESTORNADO = "estornado", "Estornado"

    data = models.DateTimeField(default=timezone.now)
    propriedade = models.ForeignKey(
        Propriedade,
        on_delete=models.PROTECT,
        related_name="recebimentos_producao",
    )
    cadpro = models.ForeignKey(CadPro, on_delete=models.PROTECT, related_name="recebimentos")
    talhao = models.ForeignKey(
        Talhao,
        on_delete=models.PROTECT,
        related_name="recebimentos_producao",
        null=True,
        blank=True,
    )
    cultura = models.ForeignKey(Cultura, on_delete=models.PROTECT, related_name="recebimentos")
    safra = models.ForeignKey(Safra, on_delete=models.PROTECT, related_name="recebimentos")
    local_armazenagem = models.ForeignKey(
        LocalEstoque,
        on_delete=models.PROTECT,
        related_name="recebimentos_producao",
    )
    motorista = models.ForeignKey(
        Motorista,
        on_delete=models.PROTECT,
        related_name="recebimentos",
        null=True,
        blank=True,
    )
    veiculo = models.ForeignKey(
        Veiculo,
        on_delete=models.PROTECT,
        related_name="recebimentos",
        null=True,
        blank=True,
    )
    placa_informada = models.CharField(max_length=20, blank=True)
    romaneio = models.CharField(max_length=80, blank=True)
    peso_bruto_kg = models.DecimalField(
        max_digits=16,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
    )
    tara_kg = models.DecimalField(
        max_digits=16,
        decimal_places=3,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    peso_liquido_kg = models.DecimalField(
        max_digits=16,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
    )
    quantidade_sacas = models.DecimalField(
        max_digits=16,
        decimal_places=3,
        default=Decimal("0"),
        editable=False,
    )
    umidade_percentual = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        default=Decimal("0"),
        validators=PERCENTUAL_VALIDATORS,
    )
    impureza_percentual = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        default=Decimal("0"),
        validators=PERCENTUAL_VALIDATORS,
    )
    defeitos_percentual = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        default=Decimal("0"),
        validators=PERCENTUAL_VALIDATORS,
    )
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.RASCUNHO)
    movimentacao = models.OneToOneField(
        "MovimentacaoGraos",
        on_delete=models.PROTECT,
        related_name="recebimento",
        null=True,
        blank=True,
        editable=False,
    )
    observacoes = models.TextField(blank=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="recebimentos_producao",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-data", "-id")
        indexes = [
            models.Index(fields=("propriedade", "safra", "cultura"), name="prod_receb_contexto_idx"),
            models.Index(fields=("status", "data"), name="prod_receb_status_data_idx"),
        ]

    def clean(self):
        erros = {}
        if self.cadpro_id and self.propriedade_id != self.cadpro.propriedade_id:
            erros["cadpro"] = "O CAD/PRO deve pertencer à propriedade informada."
        if self.talhao_id and self.propriedade_id != self.talhao.propriedade_id:
            erros["talhao"] = "O talhão deve pertencer à propriedade informada."
        if self.local_armazenagem_id and self.local_armazenagem.propriedade_id not in {None, self.propriedade_id}:
            erros["local_armazenagem"] = "O local deve pertencer à propriedade ou ser compartilhado."
        if self.tara_kg is not None and self.peso_bruto_kg is not None and self.tara_kg >= self.peso_bruto_kg:
            erros["tara_kg"] = "A tara deve ser menor que o peso bruto."
        if self.peso_liquido_kg is not None and self.peso_bruto_kg is not None and self.tara_kg is not None:
            peso_balanca = self.peso_bruto_kg - self.tara_kg
            if self.peso_liquido_kg > peso_balanca:
                erros["peso_liquido_kg"] = "O peso líquido não pode superar o peso da balança."
        if erros:
            raise ValidationError(erros)

    def __str__(self):
        return f"Recebimento {self.id or '-'} - {self.cultura}"


class SaldoGraos(models.Model):
    propriedade = models.ForeignKey(Propriedade, on_delete=models.PROTECT, related_name="saldos_graos")
    cadpro = models.ForeignKey(CadPro, on_delete=models.PROTECT, related_name="saldos")
    talhao = models.ForeignKey(
        Talhao,
        on_delete=models.PROTECT,
        related_name="saldos_graos",
        null=True,
        blank=True,
    )
    cultura = models.ForeignKey(Cultura, on_delete=models.PROTECT, related_name="saldos")
    safra = models.ForeignKey(Safra, on_delete=models.PROTECT, related_name="saldos")
    local_armazenagem = models.ForeignKey(LocalEstoque, on_delete=models.PROTECT, related_name="saldos_graos")
    quantidade_kg = models.DecimalField(max_digits=18, decimal_places=3, default=Decimal("0"))
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("propriedade__nome", "cadpro__codigo", "cultura__nome", "safra__nome")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantidade_kg__gte=0),
                name="producao_saldo_graos_nao_negativo",
            ),
            models.UniqueConstraint(
                fields=("cadpro", "talhao", "cultura", "safra", "local_armazenagem"),
                name="producao_saldo_dimensao_unico",
                nulls_distinct=False,
            ),
        ]

    @property
    def quantidade_sacas(self):
        return self.quantidade_kg / self.cultura.peso_saca_kg

    def __str__(self):
        return f"{self.cadpro} - {self.cultura} - {self.quantidade_kg} kg"


class MovimentacaoGraos(models.Model):
    class Tipo(models.TextChoices):
        ENTRADA = "entrada", "Entrada"
        SAIDA = "saida", "Saída"
        TRANSFERENCIA = "transferencia", "Transferência"
        AJUSTE_ENTRADA = "ajuste_entrada", "Ajuste de entrada"
        AJUSTE_SAIDA = "ajuste_saida", "Ajuste de saída"
        ESTORNO = "estorno", "Estorno"

    tipo = models.CharField(max_length=18, choices=Tipo.choices)
    propriedade = models.ForeignKey(Propriedade, on_delete=models.PROTECT, related_name="movimentacoes_graos")
    cadpro = models.ForeignKey(CadPro, on_delete=models.PROTECT, related_name="movimentacoes")
    talhao = models.ForeignKey(
        Talhao,
        on_delete=models.PROTECT,
        related_name="movimentacoes_graos",
        null=True,
        blank=True,
    )
    cultura = models.ForeignKey(Cultura, on_delete=models.PROTECT, related_name="movimentacoes")
    safra = models.ForeignKey(Safra, on_delete=models.PROTECT, related_name="movimentacoes")
    local_origem = models.ForeignKey(
        LocalEstoque,
        on_delete=models.PROTECT,
        related_name="saidas_graos",
        null=True,
        blank=True,
    )
    local_destino = models.ForeignKey(
        LocalEstoque,
        on_delete=models.PROTECT,
        related_name="entradas_graos",
        null=True,
        blank=True,
    )
    quantidade_kg = models.DecimalField(
        max_digits=18,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
    )
    referencia_tipo = models.CharField(max_length=40, blank=True)
    referencia_id = models.PositiveBigIntegerField(null=True, blank=True)
    estorno_de = models.OneToOneField(
        "self",
        on_delete=models.PROTECT,
        related_name="estorno",
        null=True,
        blank=True,
    )
    motivo = models.CharField(max_length=240, blank=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="movimentacoes_graos",
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-criado_em", "-id")
        indexes = [
            models.Index(fields=("propriedade", "safra", "cultura"), name="prod_mov_contexto_idx"),
            models.Index(fields=("tipo", "criado_em"), name="prod_mov_tipo_data_idx"),
        ]

    def clean(self):
        erros = {}
        if self.cadpro_id and self.propriedade_id != self.cadpro.propriedade_id:
            erros["cadpro"] = "O CAD/PRO deve pertencer à propriedade informada."
        if self.talhao_id and self.propriedade_id != self.talhao.propriedade_id:
            erros["talhao"] = "O talhão deve pertencer à propriedade informada."
        if self.tipo in {self.Tipo.SAIDA, self.Tipo.AJUSTE_SAIDA} and not self.local_origem_id:
            erros["local_origem"] = "Informe o local de origem."
        if self.tipo in {self.Tipo.ENTRADA, self.Tipo.AJUSTE_ENTRADA} and not self.local_destino_id:
            erros["local_destino"] = "Informe o local de destino."
        if self.tipo == self.Tipo.TRANSFERENCIA:
            if not self.local_origem_id or not self.local_destino_id:
                erros["local_destino"] = "A transferência exige origem e destino."
            elif self.local_origem_id == self.local_destino_id:
                erros["local_destino"] = "Origem e destino devem ser diferentes."
        if self.tipo == self.Tipo.ESTORNO and not self.estorno_de_id:
            erros["estorno_de"] = "O estorno deve referenciar uma movimentação."
        if erros:
            raise ValidationError(erros)

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.quantidade_kg} kg"


class EmbarqueProducao(models.Model):
    class Status(models.TextChoices):
        RASCUNHO = "rascunho", "Rascunho"
        CONFIRMADO = "confirmado", "Confirmado"
        ESTORNADO = "estornado", "Estornado"

    data = models.DateTimeField(default=timezone.now)
    propriedade = models.ForeignKey(Propriedade, on_delete=models.PROTECT, related_name="embarques_producao")
    cadpro = models.ForeignKey(CadPro, on_delete=models.PROTECT, related_name="embarques")
    cultura = models.ForeignKey(Cultura, on_delete=models.PROTECT, related_name="embarques")
    safra = models.ForeignKey(Safra, on_delete=models.PROTECT, related_name="embarques")
    local_armazenagem = models.ForeignKey(LocalEstoque, on_delete=models.PROTECT, related_name="embarques_producao")
    comprador = models.ForeignKey(ParceiroFinanceiro, on_delete=models.PROTECT, related_name="embarques_producao")
    contrato = models.ForeignKey(
        ContratoProducao,
        on_delete=models.PROTECT,
        related_name="embarques",
        null=True,
        blank=True,
    )
    motorista = models.ForeignKey(
        Motorista,
        on_delete=models.PROTECT,
        related_name="embarques",
        null=True,
        blank=True,
    )
    veiculo = models.ForeignKey(
        Veiculo,
        on_delete=models.PROTECT,
        related_name="embarques",
        null=True,
        blank=True,
    )
    placa_informada = models.CharField(max_length=20, blank=True)
    destino = models.CharField(max_length=240, blank=True)
    romaneio = models.CharField(max_length=80)
    nota_produtor = models.CharField(max_length=80, blank=True)
    nota_empresa = models.CharField(max_length=80, blank=True)
    quantidade_kg = models.DecimalField(
        max_digits=18,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
    )
    quantidade_sacas = models.DecimalField(
        max_digits=18,
        decimal_places=3,
        default=Decimal("0"),
        editable=False,
    )
    preco_saca = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        validators=[MinValueValidator(Decimal("0.0001"))],
    )
    valor_total = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=Decimal("0"),
        editable=False,
    )
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.RASCUNHO)
    movimentacao = models.OneToOneField(
        MovimentacaoGraos,
        on_delete=models.PROTECT,
        related_name="embarque",
        null=True,
        blank=True,
        editable=False,
    )
    lancamento_financeiro = models.OneToOneField(
        LancamentoFinanceiro,
        on_delete=models.PROTECT,
        related_name="embarque_producao",
        null=True,
        blank=True,
        editable=False,
    )
    observacoes = models.TextField(blank=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="embarques_producao",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-data", "-id")
        constraints = [
            models.UniqueConstraint(fields=("comprador", "romaneio"), name="producao_embarque_romaneio_unico")
        ]

    def clean(self):
        erros = {}
        if self.cadpro_id and self.propriedade_id != self.cadpro.propriedade_id:
            erros["cadpro"] = "O CAD/PRO deve pertencer à propriedade informada."
        if self.contrato_id:
            contexto = (
                self.contrato.propriedade_id,
                self.contrato.cadpro_id,
                self.contrato.cultura_id,
                self.contrato.safra_id,
                self.contrato.comprador_id,
            )
            atual = (self.propriedade_id, self.cadpro_id, self.cultura_id, self.safra_id, self.comprador_id)
            if contexto != atual:
                erros["contrato"] = "O contrato não corresponde ao contexto do embarque."
        if erros:
            raise ValidationError(erros)

    def __str__(self):
        return f"Embarque {self.romaneio} - {self.comprador}"


class AuditoriaProducao(models.Model):
    propriedade = models.ForeignKey(
        Propriedade,
        on_delete=models.PROTECT,
        related_name="auditorias_producao",
        null=True,
        blank=True,
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="auditorias_producao",
    )
    acao = models.CharField(max_length=60)
    entidade = models.CharField(max_length=80)
    entidade_id = models.PositiveBigIntegerField(null=True, blank=True)
    dados_anteriores = models.JSONField(default=dict, blank=True)
    dados_novos = models.JSONField(default=dict, blank=True)
    metadados = models.JSONField(default=dict, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-criado_em", "-id")
        indexes = [
            models.Index(fields=("propriedade", "criado_em"), name="prod_audit_prop_data_idx"),
            models.Index(fields=("entidade", "entidade_id"), name="prod_audit_entidade_idx"),
        ]

    def __str__(self):
        return f"{self.acao} - {self.entidade}"


class ImportacaoPlanilha(models.Model):
    class Tipo(models.TextChoices):
        RECEBIMENTOS = "recebimentos", "Recebimentos"
        MOVIMENTACOES = "movimentacoes", "Movimentações"
        EMBARQUES = "embarques", "Embarques"

    class Status(models.TextChoices):
        ENVIADA = "enviada", "Enviada"
        VALIDADA = "validada", "Validada"
        IMPORTADA = "importada", "Importada"
        ERRO = "erro", "Erro"

    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    propriedade = models.ForeignKey(Propriedade, on_delete=models.PROTECT, related_name="importacoes_producao")
    cadpro = models.ForeignKey(
        CadPro,
        on_delete=models.PROTECT,
        related_name="importacoes",
        null=True,
        blank=True,
    )
    arquivo = models.FileField(upload_to="importacoes/producao/%Y/%m/")
    nome_original = models.CharField(max_length=255)
    hash_arquivo = models.CharField(max_length=64, db_index=True)
    mapeamento = models.JSONField(default=dict, blank=True)
    previa = models.JSONField(default=list, blank=True)
    inconsistencias = models.JSONField(default=list, blank=True)
    total_linhas = models.PositiveIntegerField(default=0)
    linhas_importadas = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ENVIADA)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="importacoes_producao",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    confirmado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-criado_em", "-id")
        constraints = [
            models.UniqueConstraint(
                fields=("criado_por", "hash_arquivo", "tipo"),
                name="producao_importacao_usuario_hash_tipo_unico",
            )
        ]

    def clean(self):
        if self.cadpro_id and self.cadpro.propriedade_id != self.propriedade_id:
            raise ValidationError({"cadpro": "O CAD/PRO deve pertencer à propriedade informada."})

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.nome_original}"

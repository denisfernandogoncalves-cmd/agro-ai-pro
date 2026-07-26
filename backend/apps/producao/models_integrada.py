from decimal import Decimal
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from apps.estoque.models import LocalEstoque
from apps.financeiro.models import LancamentoFinanceiro, ParceiroFinanceiro
from apps.propriedades.models import Propriedade
from apps.talhoes.models import Talhao


class CulturaAgricola(models.Model):
    nome = models.CharField(max_length=80, unique=True)
    codigo = models.CharField(max_length=30, unique=True, null=True, blank=True)
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

    def save(self, *args, **kwargs):
        self.codigo = self.codigo or None
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nome


class SafraAgricola(models.Model):
    propriedade = models.ForeignKey(
        Propriedade,
        on_delete=models.PROTECT,
        related_name="safras_agricolas",
    )
    nome = models.CharField(max_length=20)
    data_inicio = models.DateField(null=True, blank=True)
    data_fim = models.DateField(null=True, blank=True)
    ativa = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-nome", "propriedade__nome")
        constraints = [
            models.UniqueConstraint(
                fields=("propriedade", "nome"),
                name="producao_safra_propriedade_unica",
            ),
        ]

    def clean(self):
        if self.data_inicio and self.data_fim and self.data_fim < self.data_inicio:
            raise ValidationError({"data_fim": "O fim da safra não pode anteceder o início."})

    def __str__(self):
        return f"{self.nome} - {self.propriedade}"


class CadPro(models.Model):
    propriedade = models.ForeignKey(
        Propriedade,
        on_delete=models.PROTECT,
        related_name="cadpros",
    )
    codigo = models.CharField(max_length=40)
    titular_nome = models.CharField(max_length=160)
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
                name="producao_cadpro_propriedade_codigo_unico",
            ),
        ]
        indexes = [
            models.Index(
                fields=("propriedade", "ativo"),
                name="producao_cadpro_prop_idx",
            ),
        ]

    def __str__(self):
        return f"{self.codigo} - {self.titular_nome}"


class AcessoCadPro(models.Model):
    cadpro = models.ForeignKey(
        CadPro,
        on_delete=models.CASCADE,
        related_name="acessos",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="acessos_cadpro",
    )
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("cadpro__codigo", "usuario__username")
        constraints = [
            models.UniqueConstraint(
                fields=("cadpro", "usuario"),
                name="producao_cadpro_usuario_acesso_unico",
            ),
        ]
        indexes = [
            models.Index(
                fields=("usuario", "ativo"),
                name="producao_acesso_cadpro_idx",
            ),
        ]

    def __str__(self):
        return f"{self.usuario} - {self.cadpro}"


class Motorista(models.Model):
    nome = models.CharField(max_length=160)
    documento = models.CharField(max_length=20, unique=True, null=True, blank=True)
    cnh = models.CharField(max_length=30, blank=True)
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


class Veiculo(models.Model):
    class Tipo(models.TextChoices):
        CAMINHAO = "caminhao", "Caminhão"
        CARRETA = "carreta", "Carreta"
        BITREM = "bitrem", "Bitrem"
        RODOTREM = "rodotrem", "Rodotrem"
        OUTRO = "outro", "Outro"

    placa = models.CharField(max_length=10, unique=True)
    tipo = models.CharField(max_length=12, choices=Tipo.choices, default=Tipo.CAMINHAO)
    descricao = models.CharField(max_length=160, blank=True)
    transportador = models.ForeignKey(
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
        self.placa = self.placa.upper().replace(" ", "").replace("-", "")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.placa


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
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True,
    )
    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True,
    )
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("local__nome",)

    def clean(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValidationError("Latitude e longitude devem ser informadas em conjunto.")

    def __str__(self):
        return f"{self.local} - {self.get_tipo_display()}"


class ContratoProducao(models.Model):
    class Status(models.TextChoices):
        ABERTO = "aberto", "Aberto"
        CONCLUIDO = "concluido", "Concluído"
        CANCELADO = "cancelado", "Cancelado"

    class UnidadePreco(models.TextChoices):
        KG = "kg", "Quilograma"
        SACA = "sc", "Saca"
        TONELADA = "t", "Tonelada"

    propriedade = models.ForeignKey(Propriedade, on_delete=models.PROTECT, related_name="contratos_producao")
    cadpro = models.ForeignKey(CadPro, on_delete=models.PROTECT, related_name="contratos")
    cultura = models.ForeignKey(CulturaAgricola, on_delete=models.PROTECT, related_name="contratos")
    safra = models.ForeignKey(SafraAgricola, on_delete=models.PROTECT, related_name="contratos")
    comprador = models.ForeignKey(ParceiroFinanceiro, on_delete=models.PROTECT, related_name="contratos_producao")
    numero = models.CharField(max_length=80)
    data_inicio = models.DateField(default=timezone.localdate)
    data_fim = models.DateField(null=True, blank=True)
    quantidade_kg = models.DecimalField(max_digits=16, decimal_places=3, validators=[MinValueValidator(Decimal("0.001"))])
    preco = models.DecimalField(max_digits=14, decimal_places=4, validators=[MinValueValidator(Decimal("0.0001"))])
    unidade_preco = models.CharField(max_length=2, choices=UnidadePreco.choices, default=UnidadePreco.SACA)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ABERTO)
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("data_fim", "numero")
        constraints = [
            models.UniqueConstraint(fields=("comprador", "numero"), name="producao_contrato_comprador_numero_unico"),
            models.CheckConstraint(condition=models.Q(quantidade_kg__gt=0), name="producao_contrato_quantidade_positiva"),
            models.CheckConstraint(condition=models.Q(preco__gt=0), name="producao_contrato_preco_positivo"),
        ]
        indexes = [models.Index(fields=("propriedade", "status", "data_fim"), name="producao_contrato_status_idx")]

    @property
    def quantidade_embarcada_kg(self):
        return self.embarques.filter(status="confirmado").aggregate(total=models.Sum("quantidade_kg"))["total"] or Decimal("0")

    @property
    def saldo_kg(self):
        return max(Decimal("0"), self.quantidade_kg - self.quantidade_embarcada_kg)

    def clean(self):
        erros = {}
        if self.cadpro_id and self.propriedade_id != self.cadpro.propriedade_id:
            erros["cadpro"] = "O CAD/PRO deve pertencer à propriedade."
        if self.safra_id and self.propriedade_id != self.safra.propriedade_id:
            erros["safra"] = "A safra deve pertencer à propriedade."
        if self.data_fim and self.data_fim < self.data_inicio:
            erros["data_fim"] = "O fim do contrato não pode anteceder o início."
        if erros:
            raise ValidationError(erros)

    def __str__(self):
        return f"{self.numero} - {self.comprador}"


class RecebimentoProducao(models.Model):
    class Status(models.TextChoices):
        RASCUNHO = "rascunho", "Rascunho"
        CONFIRMADO = "confirmado", "Confirmado"
        CANCELADO = "cancelado", "Cancelado"

    data = models.DateField(default=timezone.localdate)
    propriedade = models.ForeignKey(Propriedade, on_delete=models.PROTECT, related_name="recebimentos_producao")
    cadpro = models.ForeignKey(CadPro, on_delete=models.PROTECT, related_name="recebimentos")
    talhao = models.ForeignKey(Talhao, on_delete=models.PROTECT, related_name="recebimentos_producao", null=True, blank=True)
    terceiro = models.ForeignKey(ParceiroFinanceiro, on_delete=models.PROTECT, related_name="producoes_terceiros", null=True, blank=True)
    cultura = models.ForeignKey(CulturaAgricola, on_delete=models.PROTECT, related_name="recebimentos")
    safra = models.ForeignKey(SafraAgricola, on_delete=models.PROTECT, related_name="recebimentos")
    motorista = models.ForeignKey(Motorista, on_delete=models.PROTECT, related_name="recebimentos", null=True, blank=True)
    veiculo = models.ForeignKey(Veiculo, on_delete=models.PROTECT, related_name="recebimentos", null=True, blank=True)
    romaneio = models.CharField(max_length=80, blank=True)
    peso_bruto_kg = models.DecimalField(max_digits=16, decimal_places=3, validators=[MinValueValidator(Decimal("0.001"))])
    tara_kg = models.DecimalField(max_digits=16, decimal_places=3, default=Decimal("0"), validators=[MinValueValidator(Decimal("0"))])
    peso_liquido_kg = models.DecimalField(max_digits=16, decimal_places=3, validators=[MinValueValidator(Decimal("0.001"))])
    umidade_percentual = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"), validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))])
    impureza_percentual = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"), validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))])
    defeitos_percentual = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"), validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))])
    local_armazenagem = models.ForeignKey(LocalEstoque, on_delete=models.PROTECT, related_name="recebimentos_graos")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.RASCUNHO)
    observacoes = models.TextField(blank=True)
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="recebimentos_producao")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    confirmado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-data", "-id")
        indexes = [
            models.Index(fields=("propriedade", "data", "status"), name="producao_recebimento_idx"),
            models.Index(fields=("cadpro", "cultura", "safra"), name="producao_receb_dim_idx"),
        ]

    @property
    def quantidade_sacas(self):
        return self.peso_liquido_kg / self.cultura.peso_saca_kg

    @property
    def quantidade_toneladas(self):
        return self.peso_liquido_kg / Decimal("1000")

    def clean(self):
        erros = {}
        if self.cadpro_id and self.cadpro.propriedade_id != self.propriedade_id:
            erros["cadpro"] = "O CAD/PRO deve pertencer à propriedade."
        if self.safra_id and self.safra.propriedade_id != self.propriedade_id:
            erros["safra"] = "A safra deve pertencer à propriedade."
        if self.talhao_id and self.talhao.propriedade_id != self.propriedade_id:
            erros["talhao"] = "O talhão deve pertencer à propriedade."
        if not self.talhao_id and not self.terceiro_id:
            erros["talhao"] = "Informe o talhão ou o terceiro responsável pela produção."
        if self.local_armazenagem_id and self.local_armazenagem.propriedade_id not in (None, self.propriedade_id):
            erros["local_armazenagem"] = "O local deve pertencer à propriedade."
        if self.peso_bruto_kg is not None and self.tara_kg is not None:
            peso_balanca = self.peso_bruto_kg - self.tara_kg
            if peso_balanca <= 0:
                erros["tara_kg"] = "A tara deve ser menor que o peso bruto."
            elif self.peso_liquido_kg and self.peso_liquido_kg > peso_balanca:
                erros["peso_liquido_kg"] = "O peso líquido não pode superar o peso bruto descontada a tara."
        if erros:
            raise ValidationError(erros)

    def __str__(self):
        return f"Recebimento #{self.pk or 'novo'} - {self.peso_liquido_kg} kg"


class EmbarqueProducao(models.Model):
    class Status(models.TextChoices):
        RASCUNHO = "rascunho", "Rascunho"
        CONFIRMADO = "confirmado", "Confirmado"
        CANCELADO = "cancelado", "Cancelado"

    data = models.DateField(default=timezone.localdate)
    data_vencimento = models.DateField()
    propriedade = models.ForeignKey(Propriedade, on_delete=models.PROTECT, related_name="embarques_producao")
    cadpro = models.ForeignKey(CadPro, on_delete=models.PROTECT, related_name="embarques")
    cultura = models.ForeignKey(CulturaAgricola, on_delete=models.PROTECT, related_name="embarques")
    safra = models.ForeignKey(SafraAgricola, on_delete=models.PROTECT, related_name="embarques")
    local_armazenagem = models.ForeignKey(LocalEstoque, on_delete=models.PROTECT, related_name="embarques_graos")
    comprador = models.ForeignKey(ParceiroFinanceiro, on_delete=models.PROTECT, related_name="embarques_producao")
    contrato = models.ForeignKey(ContratoProducao, on_delete=models.PROTECT, related_name="embarques", null=True, blank=True)
    motorista = models.ForeignKey(Motorista, on_delete=models.PROTECT, related_name="embarques", null=True, blank=True)
    veiculo = models.ForeignKey(Veiculo, on_delete=models.PROTECT, related_name="embarques", null=True, blank=True)
    destino = models.CharField(max_length=240, blank=True)
    romaneio = models.CharField(max_length=80, blank=True)
    quantidade_kg = models.DecimalField(max_digits=16, decimal_places=3, validators=[MinValueValidator(Decimal("0.001"))])
    preco = models.DecimalField(max_digits=14, decimal_places=4, validators=[MinValueValidator(Decimal("0.0001"))])
    unidade_preco = models.CharField(max_length=2, choices=ContratoProducao.UnidadePreco.choices, default=ContratoProducao.UnidadePreco.SACA)
    valor_total = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True, editable=False)
    lancamento_financeiro = models.OneToOneField(LancamentoFinanceiro, on_delete=models.PROTECT, related_name="embarque_producao", null=True, blank=True, editable=False)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.RASCUNHO)
    observacoes = models.TextField(blank=True)
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="embarques_producao")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    confirmado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-data", "-id")
        indexes = [models.Index(fields=("propriedade", "data", "status"), name="producao_embarque_idx")]

    def clean(self):
        erros = {}
        if self.cadpro_id and self.cadpro.propriedade_id != self.propriedade_id:
            erros["cadpro"] = "O CAD/PRO deve pertencer à propriedade."
        if self.safra_id and self.safra.propriedade_id != self.propriedade_id:
            erros["safra"] = "A safra deve pertencer à propriedade."
        if self.local_armazenagem_id and self.local_armazenagem.propriedade_id not in (None, self.propriedade_id):
            erros["local_armazenagem"] = "O local deve pertencer à propriedade."
        if self.contrato_id:
            if self.contrato.propriedade_id != self.propriedade_id:
                erros["contrato"] = "O contrato deve pertencer à propriedade."
            if self.contrato.cadpro_id != self.cadpro_id:
                erros["contrato"] = "O contrato deve pertencer ao mesmo CAD/PRO."
            if self.contrato.comprador_id != self.comprador_id:
                erros["comprador"] = "O comprador deve corresponder ao contrato."
            if self.contrato.cultura_id != self.cultura_id or self.contrato.safra_id != self.safra_id:
                erros["contrato"] = "Cultura e safra devem corresponder ao contrato."
        if self.data_vencimento and self.data_vencimento < self.data:
            erros["data_vencimento"] = "O vencimento não pode anteceder o embarque."
        if erros:
            raise ValidationError(erros)

    def __str__(self):
        return f"Embarque #{self.pk or 'novo'} - {self.quantidade_kg} kg"


class MovimentoGraos(models.Model):
    class Direcao(models.TextChoices):
        ENTRADA = "entrada", "Entrada"
        SAIDA = "saida", "Saída"

    class Tipo(models.TextChoices):
        RECEBIMENTO = "recebimento", "Recebimento"
        EMBARQUE = "embarque", "Embarque"
        TRANSFERENCIA = "transferencia", "Transferência"
        AJUSTE = "ajuste", "Ajuste"
        ESTORNO = "estorno", "Estorno"

    direcao = models.CharField(max_length=8, choices=Direcao.choices)
    tipo = models.CharField(max_length=15, choices=Tipo.choices)
    data = models.DateField(default=timezone.localdate)
    propriedade = models.ForeignKey(Propriedade, on_delete=models.PROTECT, related_name="movimentos_graos")
    cadpro = models.ForeignKey(CadPro, on_delete=models.PROTECT, related_name="movimentos_graos")
    cultura = models.ForeignKey(CulturaAgricola, on_delete=models.PROTECT, related_name="movimentos_graos")
    safra = models.ForeignKey(SafraAgricola, on_delete=models.PROTECT, related_name="movimentos_graos")
    talhao = models.ForeignKey(Talhao, on_delete=models.PROTECT, related_name="movimentos_graos", null=True, blank=True)
    local_armazenagem = models.ForeignKey(LocalEstoque, on_delete=models.PROTECT, related_name="movimentos_graos")
    quantidade_kg = models.DecimalField(max_digits=16, decimal_places=3, validators=[MinValueValidator(Decimal("0.001"))])
    grupo = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)
    recebimento = models.ForeignKey(RecebimentoProducao, on_delete=models.PROTECT, related_name="movimentos", null=True, blank=True)
    embarque = models.ForeignKey(EmbarqueProducao, on_delete=models.PROTECT, related_name="movimentos", null=True, blank=True)
    movimento_origem = models.ForeignKey("self", on_delete=models.PROTECT, related_name="estornos", null=True, blank=True)
    justificativa = models.TextField(blank=True)
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="movimentos_graos")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-data", "-id")
        indexes = [
            models.Index(fields=("cadpro", "cultura", "safra", "local_armazenagem"), name="producao_saldo_graos_idx"),
            models.Index(fields=("propriedade", "data", "tipo"), name="producao_movimento_data_idx"),
        ]
        constraints = [models.CheckConstraint(condition=models.Q(quantidade_kg__gt=0), name="producao_movimento_quantidade_positiva")]

    def __str__(self):
        return f"{self.get_direcao_display()} {self.quantidade_kg} kg"


class NotaFiscalProducao(models.Model):
    class Tipo(models.TextChoices):
        PRODUTOR = "produtor", "Nota do produtor"
        EMPRESA = "empresa", "Nota da empresa"

    propriedade = models.ForeignKey(Propriedade, on_delete=models.PROTECT, related_name="notas_fiscais_producao")
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    numero = models.CharField(max_length=40)
    serie = models.CharField(max_length=10, blank=True)
    chave_acesso = models.CharField(max_length=44, blank=True)
    data_emissao = models.DateField()
    valor = models.DecimalField(max_digits=16, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    recebimento = models.ForeignKey(RecebimentoProducao, on_delete=models.PROTECT, related_name="notas_fiscais", null=True, blank=True)
    embarque = models.ForeignKey(EmbarqueProducao, on_delete=models.PROTECT, related_name="notas_fiscais", null=True, blank=True)
    arquivo = models.FileField(upload_to="producao/notas/", null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-data_emissao", "-id")
        constraints = [models.UniqueConstraint(fields=("tipo", "numero", "serie"), name="producao_nota_tipo_numero_serie_unica")]

    def clean(self):
        if bool(self.recebimento_id) == bool(self.embarque_id):
            raise ValidationError("A nota fiscal deve estar vinculada a um recebimento ou a um embarque.")
        origem = self.recebimento or self.embarque
        if origem and origem.propriedade_id != self.propriedade_id:
            raise ValidationError({"propriedade": "A propriedade deve corresponder à origem."})

    def __str__(self):
        return f"{self.get_tipo_display()} {self.numero}"


class AuditoriaProducao(models.Model):
    propriedade = models.ForeignKey(Propriedade, on_delete=models.PROTECT, related_name="auditorias_producao")
    acao = models.CharField(max_length=40)
    entidade = models.CharField(max_length=80)
    objeto_id = models.CharField(max_length=64)
    dados_anteriores = models.JSONField(default=dict, blank=True)
    dados_posteriores = models.JSONField(default=dict, blank=True)
    detalhes = models.TextField(blank=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="auditorias_producao")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-criado_em", "-id")
        indexes = [models.Index(fields=("propriedade", "entidade", "objeto_id"), name="producao_auditoria_obj_idx")]

    def __str__(self):
        return f"{self.acao} {self.entidade} #{self.objeto_id}"


class ImportacaoLegado(models.Model):
    class Tipo(models.TextChoices):
        RECEBIMENTOS = "recebimentos", "Recebimentos"
        EMBARQUES = "embarques", "Embarques"

    class Status(models.TextChoices):
        ANALISANDO = "analisando", "Analisando"
        PRONTA = "pronta", "Pronta para confirmação"
        COM_ERROS = "com_erros", "Com erros"
        IMPORTADA = "importada", "Importada"
        CANCELADA = "cancelada", "Cancelada"

    propriedade = models.ForeignKey(Propriedade, on_delete=models.PROTECT, related_name="importacoes_producao")
    cadpro = models.ForeignKey(CadPro, on_delete=models.PROTECT, related_name="importacoes")
    cultura = models.ForeignKey(CulturaAgricola, on_delete=models.PROTECT, related_name="importacoes")
    safra = models.ForeignKey(SafraAgricola, on_delete=models.PROTECT, related_name="importacoes")
    local_armazenagem = models.ForeignKey(LocalEstoque, on_delete=models.PROTECT, related_name="importacoes_producao")
    tipo = models.CharField(max_length=15, choices=Tipo.choices)
    arquivo = models.FileField(upload_to="producao/importacoes/")
    nome_arquivo = models.CharField(max_length=240)
    mapeamento = models.JSONField(default=dict, blank=True)
    colunas = models.JSONField(default=list, blank=True)
    previsualizacao = models.JSONField(default=list, blank=True)
    erros = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ANALISANDO)
    linhas_importadas = models.PositiveIntegerField(default=0)
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="importacoes_producao")
    criado_em = models.DateTimeField(auto_now_add=True)
    confirmado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-criado_em", "-id")

    def clean(self):
        erros = {}
        if self.cadpro_id and self.cadpro.propriedade_id != self.propriedade_id:
            erros["cadpro"] = "O CAD/PRO deve pertencer à propriedade."
        if self.safra_id and self.safra.propriedade_id != self.propriedade_id:
            erros["safra"] = "A safra deve pertencer à propriedade."
        if self.local_armazenagem_id and self.local_armazenagem.propriedade_id not in (None, self.propriedade_id):
            erros["local_armazenagem"] = "O local deve pertencer à propriedade."
        if erros:
            raise ValidationError(erros)

    def __str__(self):
        return self.nome_arquivo

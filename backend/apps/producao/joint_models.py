from decimal import Decimal
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from apps.estoque.models import LocalEstoque
from apps.financeiro.models import ParceiroFinanceiro
from apps.propriedades.models import Propriedade
from apps.talhoes.models import Talhao

from .grain_models import CadPro, ContratoProducao, Cultura, Motorista, Safra, Veiculo


PERCENTUAL = [MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))]
POSITIVO = [MinValueValidator(Decimal("0"))]


def gerar_codigo_lote_conjunto():
    return f"LC-{timezone.now():%Y%m%d}-{uuid4().hex[:8].upper()}"


def normalizar_placa(valor):
    return "".join(caractere for caractere in (valor or "").upper() if caractere.isalnum())


class LoteConjuntoProducao(models.Model):
    class Status(models.TextChoices):
        RASCUNHO = "rascunho", "Rascunho"
        CONFERENCIA = "conferencia", "Em conferência"
        CONFIRMADO = "confirmado", "Confirmado"
        ENCERRADO = "encerrado", "Encerrado"
        ESTORNADO = "estornado", "Estornado"

    class ModoRateio(models.TextChoices):
        SEM_RATEIO = "sem_rateio", "Conjunta sem rateio"
        AREA = "area", "Rateio automático pela área"
        MANUAL = "manual", "Rateio manual"

    codigo = models.CharField(max_length=32, unique=True, default=gerar_codigo_lote_conjunto, editable=False)
    descricao = models.CharField(max_length=240, blank=True)
    cultura = models.ForeignKey(Cultura, on_delete=models.PROTECT, related_name="lotes_conjuntos")
    variedade = models.CharField(max_length=120, blank=True)
    safra = models.ForeignKey(Safra, on_delete=models.PROTECT, related_name="lotes_conjuntos")
    data_inicio_colheita = models.DateField()
    data_final_colheita = models.DateField(null=True, blank=True)
    cadpro_responsavel = models.ForeignKey(
        CadPro,
        on_delete=models.PROTECT,
        related_name="lotes_conjuntos_responsaveis",
        null=True,
        blank=True,
    )
    local_armazenagem = models.ForeignKey(
        LocalEstoque,
        on_delete=models.PROTECT,
        related_name="lotes_conjuntos",
    )
    modo_rateio = models.CharField(max_length=16, choices=ModoRateio.choices, default=ModoRateio.SEM_RATEIO)
    area_total_cadastrada_ha = models.DecimalField(max_digits=14, decimal_places=4, default=Decimal("0"), validators=POSITIVO, editable=False)
    area_total_colhida_ha = models.DecimalField(max_digits=14, decimal_places=4, default=Decimal("0"), validators=POSITIVO, editable=False)
    peso_bruto_total_kg = models.DecimalField(max_digits=18, decimal_places=3, default=Decimal("0"), validators=POSITIVO, editable=False)
    tara_total_kg = models.DecimalField(max_digits=18, decimal_places=3, default=Decimal("0"), validators=POSITIVO, editable=False)
    peso_liquido_total_kg = models.DecimalField(max_digits=18, decimal_places=3, default=Decimal("0"), validators=POSITIVO, editable=False)
    umidade_media = models.DecimalField(max_digits=7, decimal_places=3, default=Decimal("0"), validators=PERCENTUAL, editable=False)
    impureza_media = models.DecimalField(max_digits=7, decimal_places=3, default=Decimal("0"), validators=PERCENTUAL, editable=False)
    defeitos_medios = models.DecimalField(max_digits=7, decimal_places=3, default=Decimal("0"), validators=PERCENTUAL, editable=False)
    observacoes = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.RASCUNHO)
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="lotes_conjuntos_criados")
    confirmado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="lotes_conjuntos_confirmados",
        null=True,
        blank=True,
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    confirmado_em = models.DateTimeField(null=True, blank=True)
    encerrado_em = models.DateTimeField(null=True, blank=True)
    estornado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-data_inicio_colheita", "-id")
        indexes = [
            models.Index(fields=("status", "data_inicio_colheita"), name="prod_lote_conj_status_idx"),
            models.Index(fields=("cultura", "safra"), name="prod_lote_conj_cult_idx"),
        ]

    def clean(self):
        erros = {}
        if self.data_final_colheita and self.data_final_colheita < self.data_inicio_colheita:
            erros["data_final_colheita"] = "A data final não pode ser anterior à data inicial."
        if self.cadpro_responsavel_id and self.pk:
            participante = self.participantes.filter(
                propriedade_id=self.cadpro_responsavel.propriedade_id
            ).exists()
            if not participante:
                erros["cadpro_responsavel"] = "O CAD/PRO responsável deve pertencer a uma propriedade participante."
        if erros:
            raise ValidationError(erros)

    @property
    def quantidade_toneladas(self):
        return self.peso_liquido_total_kg / Decimal("1000")

    @property
    def quantidade_sacas(self):
        return self.peso_liquido_total_kg / self.cultura.peso_saca_kg if self.cultura_id else Decimal("0")

    @property
    def produtividade_kg_ha(self):
        return self.peso_liquido_total_kg / self.area_total_colhida_ha if self.area_total_colhida_ha else Decimal("0")

    @property
    def produtividade_sacas_ha(self):
        return self.quantidade_sacas / self.area_total_colhida_ha if self.area_total_colhida_ha else Decimal("0")

    def __str__(self):
        return f"{self.codigo} - {self.cultura} - {self.safra}"


class ParticipanteLoteConjunto(models.Model):
    class MetodoRateio(models.TextChoices):
        NAO_RATEADO = "nao_rateado", "Não rateado"
        AREA = "area", "Estimado por área"
        MANUAL = "manual", "Ajustado manualmente"

    lote = models.ForeignKey(LoteConjuntoProducao, on_delete=models.CASCADE, related_name="participantes")
    propriedade = models.ForeignKey(Propriedade, on_delete=models.PROTECT, related_name="participacoes_lotes_conjuntos")
    cadpro = models.ForeignKey(CadPro, on_delete=models.PROTECT, related_name="participacoes_lotes_conjuntos", null=True, blank=True)
    area_cadastrada_ha = models.DecimalField(max_digits=14, decimal_places=4, validators=[MinValueValidator(Decimal("0.0001"))])
    area_colhida_ha = models.DecimalField(max_digits=14, decimal_places=4, validators=[MinValueValidator(Decimal("0.0001"))])
    percentual_area = models.DecimalField(max_digits=8, decimal_places=5, default=Decimal("0"), validators=PERCENTUAL, editable=False)
    quantidade_rateada_kg = models.DecimalField(max_digits=18, decimal_places=3, null=True, blank=True, validators=POSITIVO)
    metodo_rateio = models.CharField(max_length=16, choices=MetodoRateio.choices, default=MetodoRateio.NAO_RATEADO)
    excesso_area_autorizado = models.BooleanField(default=False)
    justificativa_excesso_area = models.TextField(blank=True)
    justificativa_rateio = models.TextField(blank=True)
    autorizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="areas_conjuntas_autorizadas",
        null=True,
        blank=True,
    )
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("propriedade__nome", "id")
        constraints = [
            models.UniqueConstraint(fields=("lote", "propriedade"), name="producao_lote_conjunto_propriedade_unica"),
        ]
        indexes = [models.Index(fields=("propriedade", "lote"), name="prod_part_conj_prop_idx")]

    def clean(self):
        erros = {}
        if self.cadpro_id and self.cadpro.propriedade_id != self.propriedade_id:
            erros["cadpro"] = "O CAD/PRO deve pertencer à propriedade participante."
        if self.area_colhida_ha and self.area_cadastrada_ha and self.area_colhida_ha > self.area_cadastrada_ha:
            if not self.excesso_area_autorizado or not self.justificativa_excesso_area.strip():
                erros["area_colhida_ha"] = "A área colhida supera a área disponível; é necessária autorização administrativa e justificativa."
        if self.excesso_area_autorizado and not self.autorizado_por_id:
            erros["autorizado_por"] = "Informe o administrador que autorizou o excesso de área."
        if erros:
            raise ValidationError(erros)

    def __str__(self):
        return f"{self.lote.codigo} - {self.propriedade}"


class TalhaoParticipanteLoteConjunto(models.Model):
    participante = models.ForeignKey(ParticipanteLoteConjunto, on_delete=models.CASCADE, related_name="talhoes")
    talhao = models.ForeignKey(Talhao, on_delete=models.PROTECT, related_name="participacoes_lotes_conjuntos")
    area_cadastrada_ha = models.DecimalField(max_digits=14, decimal_places=4, validators=[MinValueValidator(Decimal("0.0001"))])
    area_colhida_ha = models.DecimalField(max_digits=14, decimal_places=4, validators=[MinValueValidator(Decimal("0.0001"))])
    observacoes = models.TextField(blank=True)

    class Meta:
        ordering = ("talhao__nome", "id")
        constraints = [
            models.UniqueConstraint(fields=("participante", "talhao"), name="producao_lote_conjunto_talhao_unico"),
        ]

    def clean(self):
        erros = {}
        if self.talhao_id and self.participante_id and self.talhao.propriedade_id != self.participante.propriedade_id:
            erros["talhao"] = "O talhão deve pertencer à propriedade participante."
        if self.area_colhida_ha and self.area_cadastrada_ha and self.area_colhida_ha > self.area_cadastrada_ha:
            if not self.participante.excesso_area_autorizado:
                erros["area_colhida_ha"] = "A área colhida do talhão não pode superar sua área cadastrada."
        if erros:
            raise ValidationError(erros)


class CadProLoteConjunto(models.Model):
    lote = models.ForeignKey(LoteConjuntoProducao, on_delete=models.CASCADE, related_name="cadpros_participantes")
    participante = models.ForeignKey(
        ParticipanteLoteConjunto,
        on_delete=models.PROTECT,
        related_name="cadpros_distribuidos",
        null=True,
        blank=True,
    )
    cadpro = models.ForeignKey(CadPro, on_delete=models.PROTECT, related_name="lotes_conjuntos_participantes")
    quantidade_atribuida_kg = models.DecimalField(max_digits=18, decimal_places=3, default=Decimal("0"), validators=POSITIVO)
    metodo_rateio = models.CharField(max_length=16, choices=ParticipanteLoteConjunto.MetodoRateio.choices, default=ParticipanteLoteConjunto.MetodoRateio.NAO_RATEADO)
    justificativa = models.TextField(blank=True)
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="distribuicoes_cadpro_lote")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("cadpro__codigo", "id")
        constraints = [
            models.UniqueConstraint(fields=("lote", "cadpro"), name="producao_lote_conjunto_cadpro_unico"),
        ]

    def clean(self):
        erros = {}
        if self.cadpro_id and not self.lote.participantes.filter(propriedade_id=self.cadpro.propriedade_id).exists():
            erros["cadpro"] = "O CAD/PRO deve pertencer a uma propriedade participante."
        if self.participante_id and self.participante.propriedade_id != self.cadpro.propriedade_id:
            erros["participante"] = "O participante e o CAD/PRO devem pertencer à mesma propriedade."
        if erros:
            raise ValidationError(erros)


class CargaLoteConjunto(models.Model):
    lote = models.ForeignKey(LoteConjuntoProducao, on_delete=models.PROTECT, related_name="cargas")
    data_hora = models.DateTimeField(default=timezone.now)
    motorista = models.ForeignKey(Motorista, on_delete=models.PROTECT, related_name="cargas_lotes_conjuntos", null=True, blank=True)
    veiculo_cavalo = models.ForeignKey(Veiculo, on_delete=models.PROTECT, related_name="cargas_como_cavalo", null=True, blank=True)
    veiculo_carreta = models.ForeignKey(Veiculo, on_delete=models.PROTECT, related_name="cargas_como_carreta", null=True, blank=True)
    placa_cavalo_informada = models.CharField(max_length=20, blank=True)
    placa_carreta_informada = models.CharField(max_length=20, blank=True)
    transportadora = models.ForeignKey(ParceiroFinanceiro, on_delete=models.PROTECT, related_name="cargas_lotes_conjuntos", null=True, blank=True)
    origem = models.CharField(max_length=240, blank=True)
    destino = models.CharField(max_length=240, blank=True)
    peso_bruto_kg = models.DecimalField(max_digits=18, decimal_places=3, validators=[MinValueValidator(Decimal("0.001"))])
    tara_kg = models.DecimalField(max_digits=18, decimal_places=3, default=Decimal("0"), validators=POSITIVO)
    peso_liquido_kg = models.DecimalField(max_digits=18, decimal_places=3, validators=[MinValueValidator(Decimal("0.001"))])
    umidade_percentual = models.DecimalField(max_digits=7, decimal_places=3, default=Decimal("0"), validators=PERCENTUAL)
    impureza_percentual = models.DecimalField(max_digits=7, decimal_places=3, default=Decimal("0"), validators=PERCENTUAL)
    defeitos_percentual = models.DecimalField(max_digits=7, decimal_places=3, default=Decimal("0"), validators=PERCENTUAL)
    romaneio = models.CharField(max_length=80, blank=True)
    numero_balanca = models.CharField(max_length=80, blank=True)
    nota_fiscal = models.CharField(max_length=80, blank=True)
    local_armazenagem = models.ForeignKey(LocalEstoque, on_delete=models.PROTECT, related_name="cargas_lotes_conjuntos")
    observacoes = models.TextField(blank=True)
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="cargas_lotes_conjuntos_criadas")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("data_hora", "id")
        constraints = [
            models.UniqueConstraint(fields=("lote", "romaneio"), condition=~models.Q(romaneio=""), name="producao_carga_lote_romaneio_unico"),
        ]
        indexes = [
            models.Index(fields=("motorista", "data_hora"), name="prod_carga_conj_mot_idx"),
            models.Index(fields=("veiculo_cavalo", "data_hora"), name="prod_carga_conj_veic_idx"),
        ]

    @property
    def quantidade_sacas(self):
        return self.peso_liquido_kg / self.lote.cultura.peso_saca_kg

    def clean(self):
        erros = {}
        if self.lote_id and self.lote.status not in {LoteConjuntoProducao.Status.RASCUNHO, LoteConjuntoProducao.Status.CONFERENCIA}:
            erros["lote"] = "Cargas não podem ser alteradas após a confirmação do lote."
        if self.tara_kg >= self.peso_bruto_kg:
            erros["tara_kg"] = "A tara deve ser menor que o peso bruto."
        if self.peso_liquido_kg > self.peso_bruto_kg - self.tara_kg:
            erros["peso_liquido_kg"] = "O peso líquido não pode superar o resultado da balança."
        if self.local_armazenagem_id and self.lote_id and self.local_armazenagem_id != self.lote.local_armazenagem_id:
            erros["local_armazenagem"] = "A carga deve usar o local de armazenagem do lote."
        if erros:
            raise ValidationError(erros)

    def save(self, *args, **kwargs):
        self.placa_cavalo_informada = normalizar_placa(self.placa_cavalo_informada)
        self.placa_carreta_informada = normalizar_placa(self.placa_carreta_informada)
        super().save(*args, **kwargs)


class SaldoLoteConjunto(models.Model):
    lote = models.ForeignKey(LoteConjuntoProducao, on_delete=models.PROTECT, related_name="saldos_conjuntos")
    local_armazenagem = models.ForeignKey(LocalEstoque, on_delete=models.PROTECT, related_name="saldos_lotes_conjuntos")
    quantidade_kg = models.DecimalField(max_digits=18, decimal_places=3, default=Decimal("0"), validators=POSITIVO)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("lote__codigo", "local_armazenagem__nome")
        constraints = [
            models.UniqueConstraint(fields=("lote", "local_armazenagem"), name="producao_saldo_lote_conjunto_local_unico"),
            models.CheckConstraint(condition=models.Q(quantidade_kg__gte=0), name="producao_saldo_lote_conjunto_nao_negativo"),
        ]


class MovimentacaoLoteConjunto(models.Model):
    class Tipo(models.TextChoices):
        ENTRADA = "entrada", "Entrada"
        SAIDA = "saida", "Saída"
        TRANSFERENCIA = "transferencia", "Transferência"
        DISTRIBUICAO = "distribuicao", "Distribuição"
        AJUSTE_ENTRADA = "ajuste_entrada", "Ajuste de entrada"
        AJUSTE_SAIDA = "ajuste_saida", "Ajuste de saída"
        ESTORNO = "estorno", "Estorno"

    lote = models.ForeignKey(LoteConjuntoProducao, on_delete=models.PROTECT, related_name="movimentacoes_conjuntas")
    tipo = models.CharField(max_length=18, choices=Tipo.choices)
    local_origem = models.ForeignKey(LocalEstoque, on_delete=models.PROTECT, related_name="movimentacoes_conjuntas_saida", null=True, blank=True)
    local_destino = models.ForeignKey(LocalEstoque, on_delete=models.PROTECT, related_name="movimentacoes_conjuntas_entrada", null=True, blank=True)
    participante = models.ForeignKey(ParticipanteLoteConjunto, on_delete=models.PROTECT, related_name="movimentacoes", null=True, blank=True)
    cadpro = models.ForeignKey(CadPro, on_delete=models.PROTECT, related_name="movimentacoes_lotes_conjuntos", null=True, blank=True)
    quantidade_kg = models.DecimalField(max_digits=18, decimal_places=3, validators=[MinValueValidator(Decimal("0.001"))])
    saldo_origem_anterior = models.DecimalField(max_digits=18, decimal_places=3, null=True, blank=True)
    saldo_origem_posterior = models.DecimalField(max_digits=18, decimal_places=3, null=True, blank=True)
    saldo_destino_anterior = models.DecimalField(max_digits=18, decimal_places=3, null=True, blank=True)
    saldo_destino_posterior = models.DecimalField(max_digits=18, decimal_places=3, null=True, blank=True)
    referencia_tipo = models.CharField(max_length=50, blank=True)
    referencia_id = models.PositiveBigIntegerField(null=True, blank=True)
    motivo = models.TextField(blank=True)
    estorno_de = models.OneToOneField("self", on_delete=models.PROTECT, related_name="movimentacao_estorno", null=True, blank=True)
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="movimentacoes_lotes_conjuntos")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-criado_em", "-id")
        indexes = [
            models.Index(fields=("lote", "tipo", "criado_em"), name="prod_mov_lote_conj_idx"),
        ]


class SaidaLoteConjunto(models.Model):
    class Status(models.TextChoices):
        RASCUNHO = "rascunho", "Rascunho"
        CONFIRMADA = "confirmada", "Confirmada"
        ESTORNADA = "estornada", "Estornada"

    lote = models.ForeignKey(LoteConjuntoProducao, on_delete=models.PROTECT, related_name="saidas_conjuntas")
    data_hora = models.DateTimeField(default=timezone.now)
    local_armazenagem = models.ForeignKey(LocalEstoque, on_delete=models.PROTECT, related_name="saidas_lotes_conjuntos")
    comprador = models.ForeignKey(ParceiroFinanceiro, on_delete=models.PROTECT, related_name="saidas_lotes_conjuntos", null=True, blank=True)
    contrato = models.ForeignKey(ContratoProducao, on_delete=models.PROTECT, related_name="saidas_lotes_conjuntos", null=True, blank=True)
    motorista = models.ForeignKey(Motorista, on_delete=models.PROTECT, related_name="saidas_lotes_conjuntos", null=True, blank=True)
    veiculo_cavalo = models.ForeignKey(Veiculo, on_delete=models.PROTECT, related_name="saidas_conjuntas_como_cavalo", null=True, blank=True)
    veiculo_carreta = models.ForeignKey(Veiculo, on_delete=models.PROTECT, related_name="saidas_conjuntas_como_carreta", null=True, blank=True)
    placa_cavalo_informada = models.CharField(max_length=20, blank=True)
    placa_carreta_informada = models.CharField(max_length=20, blank=True)
    destino = models.CharField(max_length=240, blank=True)
    romaneio = models.CharField(max_length=80)
    nota_produtor = models.CharField(max_length=80, blank=True)
    nota_empresa = models.CharField(max_length=80, blank=True)
    quantidade_kg = models.DecimalField(max_digits=18, decimal_places=3, validators=[MinValueValidator(Decimal("0.001"))])
    justificativa = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.RASCUNHO)
    movimentacao = models.OneToOneField(MovimentacaoLoteConjunto, on_delete=models.PROTECT, related_name="saida_conjunta", null=True, blank=True, editable=False)
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="saidas_lotes_conjuntos_criadas")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-data_hora", "-id")
        constraints = [
            models.UniqueConstraint(fields=("lote", "romaneio"), name="producao_saida_lote_romaneio_unico"),
        ]

    def clean(self):
        erros = {}
        if self.local_armazenagem_id and self.lote_id and not self.lote.saldos_conjuntos.filter(local_armazenagem_id=self.local_armazenagem_id).exists() and self.lote.status != LoteConjuntoProducao.Status.RASCUNHO:
            erros["local_armazenagem"] = "O lote não possui saldo conjunto neste local."
        if self.contrato_id:
            if self.contrato.cultura_id != self.lote.cultura_id or self.contrato.safra_id != self.lote.safra_id:
                erros["contrato"] = "O contrato deve possuir a mesma cultura e safra do lote."
            if self.comprador_id and self.contrato.comprador_id != self.comprador_id:
                erros["comprador"] = "O comprador deve corresponder ao contrato."
        if erros:
            raise ValidationError(erros)

    def save(self, *args, **kwargs):
        self.placa_cavalo_informada = normalizar_placa(self.placa_cavalo_informada)
        self.placa_carreta_informada = normalizar_placa(self.placa_carreta_informada)
        super().save(*args, **kwargs)

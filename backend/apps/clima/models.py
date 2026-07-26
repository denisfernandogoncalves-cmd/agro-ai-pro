from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from apps.propriedades.models import Propriedade
from apps.talhoes.models import Talhao


class ConfiguracaoClima(models.Model):
    class Status(models.TextChoices):
        PENDENTE = "pendente", "Pendente"
        ATUALIZANDO = "atualizando", "Atualizando"
        ATUALIZADO = "atualizado", "Atualizado"
        ERRO = "erro", "Erro"
        SEM_LOCALIZACAO = "sem_localizacao", "Sem localização"

    propriedade = models.OneToOneField(
        Propriedade,
        on_delete=models.CASCADE,
        related_name="configuracao_clima",
    )
    ativo = models.BooleanField(default=True)
    frequencia_minutos = models.PositiveIntegerField(
        default=180,
        validators=[MinValueValidator(15), MaxValueValidator(1440)],
    )
    limite_chuva_forte_mm = models.DecimalField(max_digits=7, decimal_places=2, default=50)
    limite_geada_c = models.DecimalField(max_digits=5, decimal_places=2, default=3)
    limite_calor_c = models.DecimalField(max_digits=5, decimal_places=2, default=35)
    limite_frio_c = models.DecimalField(max_digits=5, decimal_places=2, default=8)
    limite_vento_forte_kmh = models.DecimalField(max_digits=6, decimal_places=2, default=40)
    limite_umidade_alta = models.PositiveSmallIntegerField(default=90, validators=[MaxValueValidator(100)])
    limite_umidade_baixa = models.PositiveSmallIntegerField(default=30, validators=[MaxValueValidator(100)])
    limite_deriva_vento_kmh = models.DecimalField(max_digits=6, decimal_places=2, default=15)
    limite_lavagem_chuva_mm = models.DecimalField(max_digits=6, decimal_places=2, default=5)
    dias_sem_chuva_alerta = models.PositiveSmallIntegerField(default=7)
    ultima_tentativa = models.DateTimeField(null=True, blank=True)
    ultima_atualizacao = models.DateTimeField(null=True, blank=True)
    proxima_atualizacao = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDENTE)
    erro_ultima_atualizacao = models.CharField(max_length=240, blank=True)
    falhas_consecutivas = models.PositiveIntegerField(default=0)
    total_chamadas = models.PositiveBigIntegerField(default=0)
    origem_coordenadas = models.CharField(max_length=24, blank=True)
    latitude_usada = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    longitude_usada = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    altitude_usada = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    dados_atuais = models.JSONField(default=dict, blank=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("propriedade__nome",)

    @property
    def desatualizado(self):
        return bool(
            not self.ultima_atualizacao
            or (
                self.proxima_atualizacao
                and self.proxima_atualizacao < timezone.now()
            )
        )

    def __str__(self):
        return f"Clima automático - {self.propriedade}"


class PrevisaoClima(models.Model):
    class Meta:
        ordering = ("data", "propriedade_id")
        constraints = [
            models.UniqueConstraint(
                fields=("propriedade", "data"),
                name="clima_previsao_unica_por_propriedade_data",
            ),
            models.CheckConstraint(
                condition=models.Q(chuva_mm__gte=0) | models.Q(chuva_mm__isnull=True),
                name="clima_chuva_nao_negativa",
            ),
            models.CheckConstraint(
                condition=models.Q(vento_kmh__gte=0) | models.Q(vento_kmh__isnull=True),
                name="clima_vento_nao_negativo",
            ),
        ]

    propriedade = models.ForeignKey(
        Propriedade,
        on_delete=models.PROTECT,
        related_name="previsoes_clima",
    )
    data = models.DateField()
    temperatura_min = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    temperatura_max = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    sensacao_min = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    sensacao_max = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    chuva_mm = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    umidade = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    vento_kmh = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    rajada_vento_kmh = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    direcao_vento = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MaxValueValidator(360)])
    pressao_hpa = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    cobertura_nuvens = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MaxValueValidator(100)])
    radiacao_solar_mj = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    ponto_orvalho = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    evapotranspiracao_mm = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    nascer_sol = models.DateTimeField(null=True, blank=True)
    por_sol = models.DateTimeField(null=True, blank=True)
    condicao = models.CharField(max_length=100, blank=True)
    probabilidade_chuva = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    codigo_tempo = models.PositiveSmallIntegerField(null=True, blank=True)
    alerta_agricola = models.TextField(blank=True)
    condicao_pulverizacao = models.CharField(max_length=16, blank=True)
    condicao_colheita = models.CharField(max_length=16, blank=True)
    risco_deriva = models.BooleanField(default=False)
    risco_lavagem = models.BooleanField(default=False)
    risco_estresse_hidrico = models.BooleanField(default=False)
    fonte = models.CharField(max_length=80, default="Open-Meteo")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.propriedade.nome} - {self.data}"


class PrevisaoHoraria(models.Model):
    propriedade = models.ForeignKey(
        Propriedade,
        on_delete=models.PROTECT,
        related_name="previsoes_clima_horarias",
    )
    data_hora = models.DateTimeField()
    temperatura = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    sensacao_termica = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    umidade = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MaxValueValidator(100)])
    precipitacao_mm = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    probabilidade_chuva = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MaxValueValidator(100)])
    vento_kmh = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    direcao_vento = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MaxValueValidator(360)])
    rajada_vento_kmh = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    pressao_hpa = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    cobertura_nuvens = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MaxValueValidator(100)])
    radiacao_solar = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)
    ponto_orvalho = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    evapotranspiracao_mm = models.DecimalField(max_digits=7, decimal_places=3, null=True, blank=True)
    codigo_tempo = models.PositiveSmallIntegerField(null=True, blank=True)
    condicao = models.CharField(max_length=100, blank=True)
    condicao_pulverizacao = models.CharField(max_length=16, blank=True)
    condicao_colheita = models.CharField(max_length=16, blank=True)
    risco_deriva = models.BooleanField(default=False)
    risco_lavagem = models.BooleanField(default=False)
    fonte = models.CharField(max_length=80, default="Open-Meteo")
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("data_hora",)
        constraints = [
            models.UniqueConstraint(
                fields=("propriedade", "data_hora"),
                name="clima_horaria_unica_propriedade_hora",
            )
        ]
        indexes = [
            models.Index(fields=("propriedade", "data_hora"), name="clima_prop_hora_idx")
        ]

    def __str__(self):
        return f"{self.propriedade} - {self.data_hora:%d/%m/%Y %H:%M}"


class AlertaClimatico(models.Model):
    class Nivel(models.TextChoices):
        INFORMATIVO = "informativo", "Informativo"
        ATENCAO = "atencao", "Atenção"
        CRITICO = "critico", "Crítico"

    propriedade = models.ForeignKey(
        Propriedade,
        on_delete=models.PROTECT,
        related_name="alertas_climaticos",
    )
    talhao = models.ForeignKey(
        Talhao,
        on_delete=models.PROTECT,
        related_name="alertas_climaticos",
        null=True,
        blank=True,
    )
    chave = models.CharField(max_length=160)
    tipo = models.CharField(max_length=40)
    nivel = models.CharField(max_length=12, choices=Nivel.choices)
    titulo = models.CharField(max_length=160)
    descricao = models.TextField()
    inicio = models.DateTimeField()
    fim = models.DateTimeField(null=True, blank=True)
    ativo = models.BooleanField(default=True)
    lido_em = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-inicio", "-id")
        constraints = [
            models.UniqueConstraint(
                fields=("propriedade", "chave"),
                name="clima_alerta_chave_unica_propriedade",
            )
        ]
        indexes = [
            models.Index(fields=("propriedade", "ativo", "inicio"), name="clima_alerta_ativo_idx")
        ]

    def __str__(self):
        return self.titulo


class AtualizacaoClima(models.Model):
    class Status(models.TextChoices):
        SUCESSO = "sucesso", "Sucesso"
        ERRO = "erro", "Erro"
        CACHE = "cache", "Cache"
        IGNORADA = "ignorada", "Ignorada"

    propriedade = models.ForeignKey(
        Propriedade,
        on_delete=models.PROTECT,
        related_name="atualizacoes_clima",
    )
    iniciada_em = models.DateTimeField(default=timezone.now)
    finalizada_em = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices)
    origem_coordenadas = models.CharField(max_length=24, blank=True)
    chamadas_provedor = models.PositiveSmallIntegerField(default=0)
    previsoes_diarias = models.PositiveSmallIntegerField(default=0)
    previsoes_horarias = models.PositiveSmallIntegerField(default=0)
    tipo_erro = models.CharField(max_length=80, blank=True)
    mensagem = models.CharField(max_length=240, blank=True)

    class Meta:
        ordering = ("-iniciada_em", "-id")
        indexes = [
            models.Index(fields=("propriedade", "iniciada_em"), name="clima_atualizacao_idx")
        ]

    def __str__(self):
        return f"{self.propriedade} - {self.get_status_display()}"

from django.conf import settings
from django.db import models

from apps.graos.models import LoteGraos
from apps.propriedades.models import Propriedade


class LoteImportacao(models.Model):
    class Status(models.TextChoices):
        CONCLUIDO = "concluido", "Concluído"
        COM_ERROS = "com_erros", "Concluído com erros"

    arquivo_nome = models.CharField(max_length=255)
    arquivo_tamanho = models.PositiveBigIntegerField()
    arquivo_sha256 = models.CharField(max_length=64, unique=True, editable=False)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        editable=False,
    )
    total_planilhas = models.PositiveIntegerField(default=0, editable=False)
    total_linhas = models.PositiveIntegerField(default=0, editable=False)
    total_validas = models.PositiveIntegerField(default=0, editable=False)
    total_advertencias = models.PositiveIntegerField(default=0, editable=False)
    total_erros = models.PositiveIntegerField(default=0, editable=False)
    metadados = models.JSONField(default=dict, blank=True, editable=False)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="lotes_importacao",
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-criado_em", "-id")
        verbose_name = "lote de importação"
        verbose_name_plural = "lotes de importação"
        indexes = [
            models.Index(
                fields=("status", "criado_em"),
                name="importacao_status_data_idx",
            ),
        ]

    def __str__(self):
        return f"{self.arquivo_nome} - {self.arquivo_sha256[:12]}"


class LinhaImportacao(models.Model):
    class Tipo(models.TextChoices):
        PRODUCAO = "producao", "Produção"
        SAIDA = "saida", "Saída"
        TERCEIROS = "terceiros", "Recebimento de terceiros"

    class Status(models.TextChoices):
        VALIDA = "valida", "Válida"
        ADVERTENCIA = "advertencia", "Com advertência"
        ERRO = "erro", "Com erro"

    class Associacao(models.TextChoices):
        NAO_ASSOCIADA = "nao_associada", "Não associada"
        PROPRIEDADE = "propriedade", "Propriedade associada"
        LOTE_GRAOS = "lote_graos", "Lote de grãos associado"

    lote_importacao = models.ForeignKey(
        LoteImportacao,
        on_delete=models.PROTECT,
        related_name="linhas",
    )
    sequencia = models.PositiveIntegerField()
    planilha = models.CharField(max_length=100)
    linha_origem = models.PositiveIntegerField()
    tipo = models.CharField(max_length=15, choices=Tipo.choices)
    status = models.CharField(max_length=15, choices=Status.choices, editable=False)
    hash_linha = models.CharField(max_length=64, editable=False, db_index=True)
    dados_originais = models.JSONField(default=dict, editable=False)
    dados_normalizados = models.JSONField(default=dict, editable=False)
    erros = models.JSONField(default=list, blank=True, editable=False)
    advertencias = models.JSONField(default=list, blank=True, editable=False)
    associacao = models.CharField(
        max_length=20,
        choices=Associacao.choices,
        default=Associacao.NAO_ASSOCIADA,
        editable=False,
    )
    propriedade = models.ForeignKey(
        Propriedade,
        on_delete=models.PROTECT,
        related_name="linhas_importacao",
        null=True,
        blank=True,
        editable=False,
    )
    lote_graos = models.ForeignKey(
        LoteGraos,
        on_delete=models.PROTECT,
        related_name="linhas_importacao",
        null=True,
        blank=True,
        editable=False,
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("sequencia", "id")
        verbose_name = "linha de importação"
        verbose_name_plural = "linhas de importação"
        constraints = [
            models.UniqueConstraint(
                fields=("lote_importacao", "planilha", "linha_origem"),
                name="importacao_lote_planilha_linha_unica",
            ),
        ]
        indexes = [
            models.Index(
                fields=("lote_importacao", "status"),
                name="importacao_lote_status_idx",
            ),
            models.Index(
                fields=("lote_importacao", "tipo"),
                name="importacao_lote_tipo_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.lote_importacao_id} - {self.planilha}!"
            f"{self.linha_origem} ({self.get_status_display()})"
        )

from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError


class FavoritoFiltro(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="filtros_favoritos")
    contexto = models.CharField(max_length=40)
    nome = models.CharField(max_length=80)
    filtros = models.JSONField(default=dict)
    configuracao = models.JSONField(default=dict)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("nome", "id")
        constraints = [models.UniqueConstraint(fields=("usuario", "contexto", "nome"), name="core_favorito_usuario_contexto_nome")]


class HistoricoImutavelQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError("O histórico de alterações é imutável.")

    def delete(self):
        raise ValidationError("O histórico de alterações é imutável.")


class RegistroAlteracao(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT)
    usuario_nome = models.CharField(max_length=150)
    modulo = models.CharField(max_length=40)
    entidade = models.CharField(max_length=100)
    registro_id = models.CharField(max_length=100)
    acao = models.CharField(max_length=16)
    alteracoes = models.JSONField(default=dict)
    criado_em = models.DateTimeField(auto_now_add=True, db_index=True)
    objects = HistoricoImutavelQuerySet.as_manager()

    class Meta:
        ordering = ("-criado_em", "-id")
        indexes = [models.Index(fields=("modulo", "entidade", "registro_id"), name="core_historico_registro")]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("O histórico de alterações é imutável.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("O histórico de alterações é imutável.")


class RascunhoFormulario(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    contexto = models.CharField(max_length=40)
    dados = models.JSONField(default=dict)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("usuario", "contexto"), name="core_rascunho_usuario_contexto")]


class AnexoLancamento(models.Model):
    entidade = models.CharField(max_length=30)
    registro_id = models.CharField(max_length=36)
    nome = models.CharField(max_length=160)
    tipo = models.CharField(max_length=40)
    tamanho = models.PositiveIntegerField()
    sha256 = models.CharField(max_length=64)
    conteudo = models.BinaryField(editable=False)
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    criado_em = models.DateTimeField(auto_now_add=True)
    excluido_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-criado_em", "-id")
        indexes = [models.Index(fields=("entidade", "registro_id"), name="core_anexo_registro")]
        constraints = [models.UniqueConstraint(fields=("entidade", "registro_id", "sha256"), condition=models.Q(excluido_em__isnull=True), name="core_anexo_ativo_hash")]

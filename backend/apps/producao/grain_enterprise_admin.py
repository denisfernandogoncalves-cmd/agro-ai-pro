from django.contrib import admin

from .grain_enterprise_models import (
    AuditoriaCadPro,
    ConfiguracaoCultura,
    DetalheLocalArmazenagem,
    NotaFiscalProducao,
    OrigemTerceiroRecebimento,
    TransferenciaGraos,
)


@admin.register(ConfiguracaoCultura)
class ConfiguracaoCulturaAdmin(admin.ModelAdmin):
    list_display = ("cultura", "umidade_alerta_percentual", "estoque_minimo_kg", "atualizado_em")
    search_fields = ("cultura__nome",)


@admin.register(DetalheLocalArmazenagem)
class DetalheLocalArmazenagemAdmin(admin.ModelAdmin):
    list_display = ("local", "tipo", "capacidade_kg", "ativo")
    list_filter = ("tipo", "ativo")
    search_fields = ("local__nome", "local__propriedade__nome")


@admin.register(OrigemTerceiroRecebimento)
class OrigemTerceiroRecebimentoAdmin(admin.ModelAdmin):
    list_display = ("recebimento", "terceiro", "documento_origem", "criado_em")
    search_fields = ("terceiro__nome", "documento_origem")


@admin.register(TransferenciaGraos)
class TransferenciaGraosAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "data",
        "cadpro_origem",
        "cadpro_destino",
        "cultura",
        "safra",
        "quantidade_kg",
        "status",
    )
    list_filter = ("status", "cultura", "safra")
    search_fields = (
        "cadpro_origem__codigo",
        "cadpro_destino__codigo",
        "propriedade_origem__nome",
        "propriedade_destino__nome",
    )
    readonly_fields = (
        "movimento_saida",
        "movimento_entrada",
        "confirmado_por",
        "confirmado_em",
        "criado_em",
        "atualizado_em",
    )


@admin.register(NotaFiscalProducao)
class NotaFiscalProducaoAdmin(admin.ModelAdmin):
    list_display = ("numero", "serie", "tipo", "propriedade", "cadpro", "data_emissao", "valor")
    list_filter = ("tipo", "data_emissao")
    search_fields = ("numero", "serie", "chave_acesso", "cadpro__codigo")
    readonly_fields = ("criado_por", "criado_em")


@admin.register(AuditoriaCadPro)
class AuditoriaCadProAdmin(admin.ModelAdmin):
    list_display = ("auditoria", "cadpro")
    search_fields = ("cadpro__codigo", "auditoria__acao", "auditoria__entidade")
    readonly_fields = ("auditoria", "cadpro")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

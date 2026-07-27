from django.contrib import admin

from .enterprise_models import AtualizacaoMercado, ConfiguracaoAtivoMercado, CotacaoAtivoMercado
from .models import ClimaCornBelt, CotacaoMercado, NoticiaMercado


@admin.register(CotacaoMercado)
class CotacaoMercadoAdmin(admin.ModelAdmin):
    list_display = ("produto", "data", "valor", "unidade", "fonte")
    list_filter = ("produto", "data")
    search_fields = ("produto", "fonte")
    readonly_fields = ("criado_em", "atualizado_em")


@admin.register(CotacaoAtivoMercado)
class CotacaoAtivoMercadoAdmin(admin.ModelAdmin):
    list_display = ("ativo", "intervalo", "data_hora", "fechamento", "unidade", "fonte")
    list_filter = ("ativo", "intervalo", "fonte")
    search_fields = ("ativo", "simbolo_origem", "fonte")
    date_hierarchy = "data_hora"
    readonly_fields = tuple(field.name for field in CotacaoAtivoMercado._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ConfiguracaoAtivoMercado)
class ConfiguracaoAtivoMercadoAdmin(admin.ModelAdmin):
    list_display = (
        "ativo",
        "habilitado",
        "provedor",
        "frequencia_minutos",
        "status",
        "ultima_atualizacao",
        "proxima_atualizacao",
        "total_chamadas",
    )
    list_filter = ("habilitado", "provedor", "status")
    readonly_fields = (
        "provedor",
        "simbolo",
        "ultima_tentativa",
        "ultima_atualizacao",
        "proxima_atualizacao",
        "status",
        "mensagem_erro",
        "falhas_consecutivas",
        "total_chamadas",
        "total_atualizacoes",
        "atualizado_em",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AtualizacaoMercado)
class AtualizacaoMercadoAdmin(admin.ModelAdmin):
    list_display = (
        "ativo",
        "status",
        "iniciada_em",
        "finalizada_em",
        "provedor",
        "chamadas_realizadas",
        "utilizou_cache",
    )
    list_filter = ("ativo", "status", "provedor", "utilizou_cache")
    readonly_fields = tuple(field.name for field in AtualizacaoMercado._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ClimaCornBelt)
class ClimaCornBeltAdmin(admin.ModelAdmin):
    list_display = (
        "regiao",
        "data",
        "temperatura_min",
        "temperatura_max",
        "precipitacao_mm",
        "alerta",
    )
    list_filter = ("regiao", "data")
    readonly_fields = ("criado_em", "atualizado_em")


@admin.register(NoticiaMercado)
class NoticiaMercadoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "fonte", "publicada_em", "ativa")
    list_filter = ("ativa", "fonte", "publicada_em")
    search_fields = ("titulo", "resumo", "fonte")
    readonly_fields = ("criado_em", "atualizado_em")

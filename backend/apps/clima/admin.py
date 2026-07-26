from django.contrib import admin

from .models import (
    AlertaClimatico,
    AtualizacaoClima,
    ConfiguracaoClima,
    PrevisaoClima,
    PrevisaoHoraria,
)


@admin.register(ConfiguracaoClima)
class ConfiguracaoClimaAdmin(admin.ModelAdmin):
    list_display = (
        "propriedade",
        "ativo",
        "frequencia_minutos",
        "status",
        "ultima_atualizacao",
        "proxima_atualizacao",
        "total_chamadas",
    )
    list_filter = ("ativo", "status")
    search_fields = ("propriedade__nome",)
    readonly_fields = (
        "ultima_tentativa",
        "ultima_atualizacao",
        "proxima_atualizacao",
        "status",
        "erro_ultima_atualizacao",
        "falhas_consecutivas",
        "total_chamadas",
        "origem_coordenadas",
        "latitude_usada",
        "longitude_usada",
        "altitude_usada",
        "dados_atuais",
        "atualizado_em",
    )


@admin.register(PrevisaoClima)
class PrevisaoClimaAdmin(admin.ModelAdmin):
    list_display = (
        "propriedade",
        "data",
        "temperatura_min",
        "temperatura_max",
        "chuva_mm",
        "umidade",
        "vento_kmh",
        "condicao",
    )
    search_fields = ("propriedade__nome", "condicao")
    readonly_fields = tuple(campo.name for campo in PrevisaoClima._meta.fields)
    list_filter = ("data", "condicao", "risco_deriva", "risco_lavagem")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PrevisaoHoraria)
class PrevisaoHorariaAdmin(admin.ModelAdmin):
    list_display = (
        "propriedade",
        "data_hora",
        "temperatura",
        "precipitacao_mm",
        "vento_kmh",
        "condicao_pulverizacao",
    )
    list_filter = ("condicao_pulverizacao", "condicao_colheita", "risco_deriva", "risco_lavagem")
    search_fields = ("propriedade__nome", "condicao")
    readonly_fields = tuple(campo.name for campo in PrevisaoHoraria._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AlertaClimatico)
class AlertaClimaticoAdmin(admin.ModelAdmin):
    list_display = ("propriedade", "titulo", "nivel", "inicio", "ativo", "lido_em")
    list_filter = ("nivel", "tipo", "ativo")
    search_fields = ("propriedade__nome", "titulo", "descricao")
    readonly_fields = tuple(campo.name for campo in AlertaClimatico._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AtualizacaoClima)
class AtualizacaoClimaAdmin(admin.ModelAdmin):
    list_display = (
        "propriedade",
        "iniciada_em",
        "status",
        "chamadas_provedor",
        "previsoes_diarias",
        "previsoes_horarias",
    )
    list_filter = ("status", "origem_coordenadas")
    search_fields = ("propriedade__nome", "tipo_erro")
    readonly_fields = tuple(campo.name for campo in AtualizacaoClima._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

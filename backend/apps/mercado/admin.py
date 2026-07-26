from django.contrib import admin

from .models import ClimaCornBelt, CotacaoMercado, NoticiaMercado


@admin.register(CotacaoMercado)
class CotacaoMercadoAdmin(admin.ModelAdmin):
    list_display = ("produto", "data", "valor", "unidade", "fonte")
    list_filter = ("produto", "data")
    search_fields = ("produto", "fonte")
    readonly_fields = ("criado_em", "atualizado_em")


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

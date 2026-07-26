from django.contrib import admin
from .models import PrevisaoClima


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

    search_fields = (
        "propriedade__nome",
        "condicao",
    )

    readonly_fields = ("criado_em", "atualizado_em")

    list_filter = (
        "data",
        "condicao",
    )

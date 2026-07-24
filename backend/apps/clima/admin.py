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
        "condicao",
    )

    search_fields = (
        "propriedade__nome",
        "condicao",
    )

    list_filter = (
        "data",
        "condicao",
    )
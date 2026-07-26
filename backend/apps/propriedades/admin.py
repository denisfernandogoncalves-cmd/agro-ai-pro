from django.contrib import admin
from .models import Propriedade


@admin.register(Propriedade)
class PropriedadeAdmin(admin.ModelAdmin):

    list_display = (
        "nome",
        "municipio",
        "uf",
        "area_hectares",
        "area_calculada_hectares",
        "criado_em",
    )

    search_fields = (
        "nome",
        "municipio",
        "proprietario",
    )

    readonly_fields = (
        "geometria_geojson",
        "area_calculada_hectares",
    )

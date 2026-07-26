from django.contrib import admin

from .models import AcessoPropriedade, Propriedade


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
    search_fields = ("nome", "municipio", "proprietario")
    readonly_fields = ("geometria_geojson", "area_calculada_hectares")


@admin.register(AcessoPropriedade)
class AcessoPropriedadeAdmin(admin.ModelAdmin):
    list_display = ("propriedade", "usuario", "papel", "ativo", "atualizado_em")
    list_filter = ("papel", "ativo")
    search_fields = (
        "propriedade__nome",
        "usuario__username",
        "usuario__first_name",
        "usuario__last_name",
    )
    autocomplete_fields = ("propriedade", "usuario")

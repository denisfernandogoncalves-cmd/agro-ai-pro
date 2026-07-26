from django.contrib import admin
from .models import HistoricoAgronomico, Talhao


class HistoricoAgronomicoInline(admin.TabularInline):
    model = HistoricoAgronomico
    extra = 0


@admin.register(Talhao)
class TalhaoAdmin(admin.ModelAdmin):

    list_display = (
        "nome",
        "propriedade",
        "area_hectares",
        "area_calculada_hectares",
        "cultura_atual",
        "safra",
        "tipo_solo",
        "produtividade_esperada",
        "produtividade_realizada",
    )

    list_filter = (
        "cultura_atual",
        "safra",
        "propriedade",
    )

    search_fields = (
        "nome",
        "propriedade__nome",
        "cultura_atual",
    )

    readonly_fields = (
        "geometria_geojson",
        "area_calculada_hectares",
        "criado_em",
        "atualizado_em",
    )
    inlines = (HistoricoAgronomicoInline,)


@admin.register(HistoricoAgronomico)
class HistoricoAgronomicoAdmin(admin.ModelAdmin):
    list_display = (
        "talhao",
        "data_referencia",
        "cultura",
        "safra",
        "produtividade_esperada",
        "produtividade_realizada",
    )
    list_filter = ("cultura", "safra", "data_referencia")
    search_fields = ("talhao__nome", "talhao__propriedade__nome", "cultura", "safra")
    readonly_fields = ("criado_em", "atualizado_em")

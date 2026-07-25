from django.contrib import admin
from .models import Talhao


@admin.register(Talhao)
class TalhaoAdmin(admin.ModelAdmin):

    list_display = (
        "nome",
        "propriedade",
        "area_hectares",
        "cultura_atual",
        "safra",
        "tipo_solo",
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
        "criado_em",
    )
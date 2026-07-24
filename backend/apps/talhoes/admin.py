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
    )

    search_fields = (
        "nome",
        "propriedade__nome",
    )
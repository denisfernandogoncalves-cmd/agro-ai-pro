from django.contrib import admin

from .models import DevolucaoVendaGraos, EntregaVendaGraos, VendaGraos


@admin.register(VendaGraos)
class VendaGraosAdmin(admin.ModelAdmin):
    list_display = (
        "numero_contrato", "cliente_nome", "status", "quantidade_kg",
        "quantidade_entregue_kg", "data_contrato",
    )
    list_filter = ("status", "data_contrato")
    search_fields = ("numero_contrato", "cliente_nome")


admin.site.register(EntregaVendaGraos)
admin.site.register(DevolucaoVendaGraos)

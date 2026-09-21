from django.contrib import admin

from .models import DevolucaoVendaGraos, EntregaVendaGraos, VendaGraos


class TrilhaComercialSomenteLeituraAdmin(admin.ModelAdmin):
    """Consulta operacional; mutações passam pelos serviços transacionais."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(VendaGraos)
class VendaGraosAdmin(TrilhaComercialSomenteLeituraAdmin):
    list_display = (
        "numero_contrato", "cliente_nome", "status", "quantidade_kg",
        "quantidade_entregue_kg", "data_contrato",
    )
    list_filter = ("status", "data_contrato")
    search_fields = ("numero_contrato", "cliente_nome")


@admin.register(EntregaVendaGraos)
class EntregaVendaGraosAdmin(TrilhaComercialSomenteLeituraAdmin):
    list_display = ("venda", "quantidade_kg", "data_entrega", "criado_em")
    search_fields = ("venda__numero_contrato", "referencia_externa")


@admin.register(DevolucaoVendaGraos)
class DevolucaoVendaGraosAdmin(TrilhaComercialSomenteLeituraAdmin):
    list_display = ("venda", "quantidade_kg", "data_devolucao", "criado_em")
    search_fields = ("venda__numero_contrato", "referencia_externa")

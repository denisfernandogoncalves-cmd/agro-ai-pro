from django.contrib import admin

from .models import ArmazemGraos, LoteGraos, MovimentacaoGraos


@admin.register(ArmazemGraos)
class ArmazemGraosAdmin(admin.ModelAdmin):
    list_display = ("nome", "propriedade", "capacidade_kg", "ativo")
    list_filter = ("ativo", "propriedade")
    search_fields = ("nome", "propriedade__nome")


@admin.register(LoteGraos)
class LoteGraosAdmin(admin.ModelAdmin):
    list_display = ("codigo", "cultura", "safra", "armazem", "ativo")
    list_filter = ("ativo", "cultura", "safra", "armazem")
    search_fields = ("codigo", "cultura", "safra", "armazem__nome")


@admin.register(MovimentacaoGraos)
class MovimentacaoGraosAdmin(admin.ModelAdmin):
    list_display = (
        "tipo",
        "lote",
        "quantidade_kg",
        "data_movimento",
        "criado_por",
    )
    list_filter = ("tipo", "data_movimento", "lote__armazem")
    search_fields = (
        "lote__codigo",
        "referencia_externa",
        "chave_idempotencia",
    )
    readonly_fields = (
        "tipo",
        "lote",
        "quantidade_kg",
        "data_movimento",
        "referencia_externa",
        "chave_idempotencia",
        "observacoes",
        "criado_por",
        "criado_em",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

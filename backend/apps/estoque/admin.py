from django.contrib import admin

from .models import (
    LocalEstoque,
    LoteEstoque,
    MovimentacaoEstoque,
    ProdutoEstoque,
)


@admin.register(ProdutoEstoque)
class ProdutoEstoqueAdmin(admin.ModelAdmin):
    list_display = ("nome", "categoria", "unidade", "estoque_minimo", "ativo")
    list_filter = ("categoria", "unidade", "ativo")
    search_fields = ("nome", "fabricante")


admin.site.register(LocalEstoque)


@admin.register(LoteEstoque)
class LoteEstoqueAdmin(admin.ModelAdmin):
    list_display = ("codigo", "produto", "local", "data_validade", "ativo")
    list_filter = ("ativo", "data_validade", "local")
    search_fields = ("codigo", "produto__nome")


@admin.register(MovimentacaoEstoque)
class MovimentacaoEstoqueAdmin(admin.ModelAdmin):
    list_display = (
        "data_movimento",
        "tipo",
        "lote",
        "quantidade",
        "custo_unitario",
        "criado_por",
    )
    list_filter = ("tipo", "data_movimento", "lote__local")
    search_fields = (
        "lote__produto__nome",
        "lote__codigo",
        "documento_fiscal",
    )
    readonly_fields = (
        "tipo",
        "lote",
        "quantidade",
        "custo_unitario",
        "data_movimento",
        "documento_fiscal",
        "propriedade",
        "safra",
        "observacoes",
        "criado_por",
        "criado_em",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

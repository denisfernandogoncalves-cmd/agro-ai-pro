from django.contrib import admin

from .models import (
    CategoriaFinanceira,
    CentroCusto,
    LancamentoFinanceiro,
    ParceiroFinanceiro,
)


admin.site.register(CategoriaFinanceira)
admin.site.register(ParceiroFinanceiro)
admin.site.register(CentroCusto)


@admin.register(LancamentoFinanceiro)
class LancamentoFinanceiroAdmin(admin.ModelAdmin):
    list_display = (
        "descricao",
        "tipo",
        "valor",
        "data_vencimento",
        "status",
        "propriedade",
        "safra",
    )
    list_filter = ("tipo", "status", "categoria", "data_vencimento")
    search_fields = ("descricao", "parceiro__nome", "safra")
    readonly_fields = ("criado_em", "atualizado_em")

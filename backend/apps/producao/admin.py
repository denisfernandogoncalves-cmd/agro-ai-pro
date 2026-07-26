from django.contrib import admin

from .models import InsumoOperacao, OperacaoAgricola


class InsumoOperacaoInline(admin.TabularInline):
    model = InsumoOperacao
    extra = 0
    readonly_fields = ("movimentacao_estoque",)

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(OperacaoAgricola)
class OperacaoAgricolaAdmin(admin.ModelAdmin):
    list_display = (
        "descricao",
        "tipo",
        "talhao",
        "data_planejada",
        "status",
        "responsavel",
    )
    list_filter = ("tipo", "status", "data_planejada")
    search_fields = ("descricao", "talhao__nome", "responsavel")
    inlines = (InsumoOperacaoInline,)

    def get_readonly_fields(self, request, obj=None):
        return tuple(campo.name for campo in self.model._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

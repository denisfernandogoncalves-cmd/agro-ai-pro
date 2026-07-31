from django.contrib import admin

from .models import LinhaImportacao, LoteImportacao


class SomenteLeituraAdminMixin:
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(LoteImportacao)
class LoteImportacaoAdmin(SomenteLeituraAdminMixin, admin.ModelAdmin):
    list_display = (
        "arquivo_nome",
        "status",
        "total_linhas",
        "total_advertencias",
        "total_erros",
        "criado_por",
        "criado_em",
    )
    list_filter = ("status", "criado_em")
    search_fields = ("arquivo_nome", "arquivo_sha256", "criado_por__username")
    readonly_fields = tuple(
        campo.name for campo in LoteImportacao._meta.fields
    )


@admin.register(LinhaImportacao)
class LinhaImportacaoAdmin(SomenteLeituraAdminMixin, admin.ModelAdmin):
    list_display = (
        "lote_importacao",
        "sequencia",
        "planilha",
        "linha_origem",
        "tipo",
        "status",
        "associacao",
    )
    list_filter = ("tipo", "status", "associacao", "planilha")
    search_fields = (
        "lote_importacao__arquivo_nome",
        "hash_linha",
        "dados_normalizados",
    )
    readonly_fields = tuple(
        campo.name for campo in LinhaImportacao._meta.fields
    )

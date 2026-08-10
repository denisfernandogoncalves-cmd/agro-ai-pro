from django.contrib import admin

from .models import CADPro, CADProPropriedade


@admin.register(CADPro)
class CADProAdmin(admin.ModelAdmin):
    list_display = ("codigo", "descricao", "ativo", "atualizado_em")
    list_filter = ("ativo",)
    search_fields = ("codigo", "codigo_normalizado", "descricao")
    readonly_fields = ("id", "codigo_normalizado", "criado_em", "atualizado_em")


@admin.register(CADProPropriedade)
class CADProPropriedadeAdmin(admin.ModelAdmin):
    list_display = ("cad_pro", "propriedade", "ativo", "atualizado_em")
    list_filter = ("ativo",)
    search_fields = (
        "cad_pro__codigo",
        "cad_pro__descricao",
        "propriedade__nome",
    )
    autocomplete_fields = ("cad_pro", "propriedade")
    readonly_fields = ("id", "criado_em", "atualizado_em")

from django.contrib import admin

from .models import (
    AcessoCadPro,
    AuditoriaProducao,
    CadPro,
    ContratoProducao,
    Cultura,
    EmbarqueProducao,
    ImportacaoPlanilha,
    InsumoOperacao,
    Motorista,
    MovimentacaoGraos,
    OperacaoAgricola,
    RecebimentoProducao,
    Safra,
    SaldoGraos,
    Veiculo,
)


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


@admin.register(Cultura)
class CulturaAdmin(admin.ModelAdmin):
    list_display = ("nome", "codigo", "peso_saca_kg", "ativa")
    list_filter = ("ativa",)
    search_fields = ("nome", "codigo")


@admin.register(Safra)
class SafraAdmin(admin.ModelAdmin):
    list_display = ("nome", "data_inicio", "data_fim", "ativa")
    list_filter = ("ativa",)
    search_fields = ("nome",)


@admin.register(CadPro)
class CadProAdmin(admin.ModelAdmin):
    list_display = ("codigo", "propriedade", "titular", "ativo")
    list_filter = ("ativo", "propriedade")
    search_fields = ("codigo", "titular", "documento", "propriedade__nome")


@admin.register(AcessoCadPro)
class AcessoCadProAdmin(admin.ModelAdmin):
    list_display = ("cadpro", "usuario", "ativo", "criado_em")
    list_filter = ("ativo", "cadpro__propriedade")
    search_fields = ("cadpro__codigo", "usuario__username", "cadpro__propriedade__nome")


@admin.register(Motorista)
class MotoristaAdmin(admin.ModelAdmin):
    list_display = ("nome", "documento", "telefone", "terceiro", "ativo")
    list_filter = ("ativo",)
    search_fields = ("nome", "documento", "telefone")


@admin.register(Veiculo)
class VeiculoAdmin(admin.ModelAdmin):
    list_display = ("placa", "tipo", "motorista_padrao", "terceiro", "ativo")
    list_filter = ("tipo", "ativo")
    search_fields = ("placa", "descricao", "motorista_padrao__nome")


@admin.register(ContratoProducao)
class ContratoProducaoAdmin(admin.ModelAdmin):
    list_display = ("numero", "comprador", "propriedade", "cadpro", "cultura", "safra", "quantidade_kg", "status")
    list_filter = ("status", "cultura", "safra", "propriedade")
    search_fields = ("numero", "comprador__nome", "cadpro__codigo")


@admin.register(RecebimentoProducao)
class RecebimentoProducaoAdmin(admin.ModelAdmin):
    list_display = ("id", "data", "propriedade", "cadpro", "cultura", "safra", "peso_liquido_kg", "status")
    list_filter = ("status", "cultura", "safra", "propriedade")
    search_fields = ("romaneio", "cadpro__codigo", "motorista__nome", "placa_informada")
    readonly_fields = ("quantidade_sacas", "movimentacao", "criado_por", "criado_em", "atualizado_em")


@admin.register(EmbarqueProducao)
class EmbarqueProducaoAdmin(admin.ModelAdmin):
    list_display = ("romaneio", "data", "comprador", "propriedade", "cadpro", "quantidade_kg", "valor_total", "status")
    list_filter = ("status", "cultura", "safra", "propriedade")
    search_fields = ("romaneio", "nota_produtor", "nota_empresa", "comprador__nome")
    readonly_fields = ("quantidade_sacas", "valor_total", "movimentacao", "lancamento_financeiro", "criado_por", "criado_em", "atualizado_em")


@admin.register(SaldoGraos)
class SaldoGraosAdmin(admin.ModelAdmin):
    list_display = ("propriedade", "cadpro", "cultura", "safra", "local_armazenagem", "quantidade_kg", "atualizado_em")
    list_filter = ("cultura", "safra", "propriedade", "local_armazenagem")
    search_fields = ("cadpro__codigo", "cultura__nome", "safra__nome", "local_armazenagem__nome")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(MovimentacaoGraos)
class MovimentacaoGraosAdmin(admin.ModelAdmin):
    list_display = ("tipo", "propriedade", "cadpro", "cultura", "safra", "quantidade_kg", "criado_por", "criado_em")
    list_filter = ("tipo", "cultura", "safra", "propriedade")
    search_fields = ("cadpro__codigo", "referencia_tipo", "motivo")

    def get_readonly_fields(self, request, obj=None):
        return tuple(field.name for field in self.model._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AuditoriaProducao)
class AuditoriaProducaoAdmin(admin.ModelAdmin):
    list_display = ("acao", "entidade", "entidade_id", "propriedade", "usuario", "criado_em")
    list_filter = ("acao", "entidade", "propriedade")
    search_fields = ("acao", "entidade", "usuario__username")

    def get_readonly_fields(self, request, obj=None):
        return tuple(field.name for field in self.model._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ImportacaoPlanilha)
class ImportacaoPlanilhaAdmin(admin.ModelAdmin):
    list_display = ("nome_original", "tipo", "propriedade", "cadpro", "status", "total_linhas", "linhas_importadas", "criado_por", "criado_em")
    list_filter = ("tipo", "status", "propriedade")
    search_fields = ("nome_original", "hash_arquivo", "cadpro__codigo", "criado_por__username")
    readonly_fields = ("hash_arquivo", "mapeamento", "previa", "inconsistencias", "total_linhas", "linhas_importadas", "status", "criado_por", "criado_em", "confirmado_em")

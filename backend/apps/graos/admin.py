from django.contrib import admin

from .models import (
    ArmazemGraos,
    CargaColhida,
    GrupoColheita,
    LoteGraos,
    MovimentacaoGraos,
    OrigemSaldoGraos,
    PosicaoSaldoGraos,
    ReservaSaldoGraos,
)


@admin.register(ArmazemGraos)
class ArmazemGraosAdmin(admin.ModelAdmin):
    list_display = ("nome", "propriedade", "capacidade_kg", "ativo")
    list_filter = ("ativo", "propriedade")
    search_fields = ("nome", "propriedade__nome")


@admin.register(LoteGraos)
class LoteGraosAdmin(admin.ModelAdmin):
    list_display = ("codigo", "cad_pro", "cultura", "safra", "classificacao_codigo", "armazem", "ativo")
    list_filter = ("ativo", "cultura", "safra", "classificacao_codigo", "armazem")
    search_fields = ("codigo", "cultura", "safra", "armazem__nome")


@admin.register(GrupoColheita)
class GrupoColheitaAdmin(admin.ModelAdmin):
    list_display = ("nome", "propriedade", "cad_pro", "cultura", "safra", "ativo")
    list_filter = ("ativo", "cultura", "safra", "propriedade")
    search_fields = ("nome", "propriedade__nome", "cad_pro__codigo")


@admin.register(CargaColhida)
class CargaColhidaAdmin(admin.ModelAdmin):
    list_display = (
        "data_colheita",
        "placa",
        "grupo_colheita",
        "armazem",
        "peso_bruto_kg",
        "peso_liquido_kg",
        "sacas_60kg",
    )
    list_filter = ("data_colheita", "destinado_semente", "grupo_colheita", "armazem")
    search_fields = ("placa", "grupo_colheita__nome", "local_colheita")
    readonly_fields = tuple(campo.name for campo in CargaColhida._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(MovimentacaoGraos)
class MovimentacaoGraosAdmin(admin.ModelAdmin):
    list_display = (
        "tipo",
        "operacao",
        "lote",
        "quantidade_kg",
        "data_movimento",
        "criado_por",
    )
    list_filter = ("tipo", "operacao", "data_movimento", "lote__armazem")
    search_fields = (
        "lote__codigo",
        "referencia_externa",
        "chave_idempotencia",
    )
    readonly_fields = (
        "tipo",
        "operacao",
        "lote",
        "posicao",
        "origem",
        "reserva",
        "estorno_de",
        "quantidade_kg",
        "delta_fisico_kg",
        "delta_comprometido_kg",
        "snapshot_anterior",
        "snapshot_posterior",
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


class SomenteLeituraAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return bool(obj is not None and request.method in ("GET", "HEAD"))

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PosicaoSaldoGraos)
class PosicaoSaldoGraosAdmin(SomenteLeituraAdmin):
    list_display = ("cad_pro", "cultura", "safra", "classificacao_codigo", "armazem", "saldo_fisico_kg", "saldo_comprometido_kg", "versao")
    list_filter = ("cultura", "safra", "classificacao_codigo", "armazem")
    search_fields = ("cad_pro__codigo", "cultura", "safra", "armazem__nome")


@admin.register(OrigemSaldoGraos)
class OrigemSaldoGraosAdmin(SomenteLeituraAdmin):
    list_display = ("tipo", "chave_idempotencia", "referencia_externa", "criado_por", "criado_em")
    list_filter = ("tipo", "criado_em")
    search_fields = ("chave_idempotencia", "referencia_externa")


@admin.register(ReservaSaldoGraos)
class ReservaSaldoGraosAdmin(SomenteLeituraAdmin):
    list_display = ("id", "posicao", "quantidade_kg", "saldo_reservado_kg", "status", "criado_em")
    list_filter = ("status", "criado_em")

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ArmazemGraosViewSet,
    CargaColhidaViewSet,
    LoteGraosViewSet,
    MovimentacaoGraosViewSet,
    OrigemSaldoGraosViewSet,
    ReservaSaldoGraosViewSet,
    SaldoGraosViewSet,
)


router = DefaultRouter()
router.register("armazens", ArmazemGraosViewSet, basename="armazens-graos")
router.register("cargas-colhidas", CargaColhidaViewSet, basename="cargas-colhidas")
router.register("lotes", LoteGraosViewSet, basename="lotes-graos")
router.register(
    "movimentacoes",
    MovimentacaoGraosViewSet,
    basename="movimentacoes-graos",
)
router.register("saldos", SaldoGraosViewSet, basename="saldos-graos")
router.register("origens-saldo", OrigemSaldoGraosViewSet, basename="origens-saldo-graos")
router.register("reservas", ReservaSaldoGraosViewSet, basename="reservas-saldo-graos")

from .transferencias_correcoes import CorrecaoTransferenciaView
from .terceiros import TerceirosView
from .conferencia_pesagem import ConferenciaPesagemView
from .resumo_terceiros import ResumoTerceirosView
from .extrato_terceiros import ExtratoTerceirosView
from .romaneios_cargas import RomaneioCargaView
from .cadastro_terceiros import CadastroTerceirosView
from .romaneios_retiradas import RomaneioRetiradaView
from .conferencia_operacional import ConciliacaoEstoqueView, VinculoTerceiroView

urlpatterns = [
    path('terceiros/transferencias/<int:pk>/pdf/',RomaneioRetiradaView.as_view(tipo='transferencia')),
    path('terceiros/transferencias/<int:pk>/excel/',RomaneioRetiradaView.as_view(tipo='transferencia',excel=True)),
    path('conciliacao-estoque/', ConciliacaoEstoqueView.as_view()),
    path('terceiros/entradas/<int:pk>/vincular/', VinculoTerceiroView.as_view()),
    path('terceiros/movimentos/<int:pk>/pdf/',RomaneioRetiradaView.as_view(),name='retirada-pdf'),
    path('terceiros/movimentos/<int:pk>/excel/',RomaneioRetiradaView.as_view(excel=True),name='retirada-excel'),
    path("terceiros/cadastros/", CadastroTerceirosView.as_view(), name="terceiros-cadastros"),
    path("terceiros/cadastros/<int:pk>/", CadastroTerceirosView.as_view(), name="terceiro-cadastro-detalhe"),
    path("cargas-colhidas/<int:pk>/pdf/", RomaneioCargaView.as_view(), name="carga-pdf"),
    path("cargas-colhidas/<int:pk>/excel/", RomaneioCargaView.as_view(excel=True), name="carga-excel"),
    path("terceiros/extrato/", ExtratoTerceirosView.as_view(), name="terceiros-extrato"),
    path("cargas-colhidas/conferencia-pesagem/previa/", ConferenciaPesagemView.as_view(), name="conferencia-pesagem"),
    path("terceiros/resumo/", ResumoTerceirosView.as_view(), name="terceiros-resumo"),
    path("terceiros/resumo/excel/", ResumoTerceirosView.as_view(excel=True), name="terceiros-resumo-excel"),
    path("terceiros/entradas/<int:pk>/pdf/", TerceirosView.as_view(tipo="pdf"), name="terceiros-pdf"),
    path("terceiros/entradas/<int:pk>/excel/", TerceirosView.as_view(tipo="excel"), name="terceiros-excel"),
    path("terceiros/previa/", TerceirosView.as_view(tipo="previa"), name="terceiros-previa"),
    path("terceiros/entradas/<int:pk>/", TerceirosView.as_view(), name="terceiros-entrada-detalhe"),
    path("terceiros/entradas/", TerceirosView.as_view(), name="terceiros-entradas"),
    path("terceiros/entradas/<int:pk>/registrar-saida/", TerceirosView.as_view(tipo="saida"), name="terceiros-saida"),
    path("terceiros/entradas/<int:pk>/transferir/", TerceirosView.as_view(tipo="transferencia"), name="terceiros-transferencia"),
    path("terceiros/movimentos/<int:pk>/estornar/", TerceirosView.as_view(tipo="estorno"), name="terceiros-estorno"),
    path("transferencias/<int:pk>/", CorrecaoTransferenciaView.as_view(), name="correcao-transferencia-saldo"),
    path(
        "producoes/creditar/",
        SaldoGraosViewSet.as_view({"post": "creditar_producao"}),
        name="graos-producoes-creditar",
    ),
    path(
        "ajustes/",
        SaldoGraosViewSet.as_view({"post": "registrar_ajuste"}),
        name="graos-ajustes",
    ),
    path(
        "transferencias/",
        SaldoGraosViewSet.as_view({"post": "transferir"}),
        name="graos-transferencias",
    ),
    path("", include(router.urls)),
]

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .grain_views import (
    AcessoCadProViewSet,
    AuditoriaProducaoViewSet,
    CadProViewSet,
    ContratoProducaoViewSet,
    CulturaViewSet,
    EmbarqueProducaoViewSet,
    ImportacaoPlanilhaViewSet,
    MotoristaViewSet,
    MovimentacaoGraosViewSet,
    ProducaoDashboardView,
    RecebimentoProducaoViewSet,
    RelatorioProducaoView,
    SafraViewSet,
    SaldoGraosViewSet,
    VeiculoViewSet,
)
from .views import InsumoOperacaoViewSet, OperacaoAgricolaViewSet


router = DefaultRouter()
router.register("operacoes", OperacaoAgricolaViewSet, basename="operacoes")
router.register("insumos", InsumoOperacaoViewSet, basename="insumos")
router.register("culturas", CulturaViewSet, basename="culturas")
router.register("safras", SafraViewSet, basename="safras")
router.register("cadpros", CadProViewSet, basename="cadpros")
router.register("acessos-cadpro", AcessoCadProViewSet, basename="acessos-cadpro")
router.register("motoristas", MotoristaViewSet, basename="motoristas")
router.register("veiculos", VeiculoViewSet, basename="veiculos")
router.register("contratos", ContratoProducaoViewSet, basename="contratos-producao")
router.register("recebimentos", RecebimentoProducaoViewSet, basename="recebimentos-producao")
router.register("embarques", EmbarqueProducaoViewSet, basename="embarques-producao")
router.register("movimentacoes-graos", MovimentacaoGraosViewSet, basename="movimentacoes-graos")
router.register("saldos-graos", SaldoGraosViewSet, basename="saldos-graos")
router.register("auditoria", AuditoriaProducaoViewSet, basename="auditoria-producao")
router.register("importacoes", ImportacaoPlanilhaViewSet, basename="importacoes-producao")

urlpatterns = [
    path("", include(router.urls)),
    path("dashboard-integrado/", ProducaoDashboardView.as_view(), name="producao-dashboard-integrado"),
    path("relatorios-integrados/", RelatorioProducaoView.as_view(), name="producao-relatorios-integrados"),
]

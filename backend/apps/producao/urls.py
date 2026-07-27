from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .grain_safe_views import (
    EmbarqueProducaoSeguroViewSet,
    ImportacaoPlanilhaSeguraViewSet,
    RecebimentoProducaoSeguroViewSet,
)
from .grain_views import (
    AcessoCadProViewSet,
    AuditoriaProducaoViewSet,
    CadProViewSet,
    ContratoProducaoViewSet,
    CulturaViewSet,
    MotoristaViewSet,
    MovimentacaoGraosViewSet,
    ProducaoDashboardView,
    RelatorioProducaoView,
    SafraViewSet,
    SaldoGraosViewSet,
    VeiculoViewSet,
)
from .joint_safe_views import LoteConjuntoProducaoSeguroViewSet
from .joint_views import (
    CargaLoteConjuntoViewSet,
    MovimentacaoLoteConjuntoViewSet,
    RelatorioLoteConjuntoView,
    SaidaLoteConjuntoViewSet,
    SaldoLoteConjuntoViewSet,
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
router.register("recebimentos", RecebimentoProducaoSeguroViewSet, basename="recebimentos-producao")
router.register("embarques", EmbarqueProducaoSeguroViewSet, basename="embarques-producao")
router.register("movimentacoes-graos", MovimentacaoGraosViewSet, basename="movimentacoes-graos")
router.register("saldos-graos", SaldoGraosViewSet, basename="saldos-graos")
router.register("auditoria", AuditoriaProducaoViewSet, basename="auditoria-producao")
router.register("importacoes", ImportacaoPlanilhaSeguraViewSet, basename="importacoes-producao")
router.register("lotes-conjuntos", LoteConjuntoProducaoSeguroViewSet, basename="lotes-conjuntos")
router.register("cargas-lotes-conjuntos", CargaLoteConjuntoViewSet, basename="cargas-lotes-conjuntos")
router.register("saidas-lotes-conjuntos", SaidaLoteConjuntoViewSet, basename="saidas-lotes-conjuntos")
router.register("saldos-lotes-conjuntos", SaldoLoteConjuntoViewSet, basename="saldos-lotes-conjuntos")
router.register("movimentacoes-lotes-conjuntos", MovimentacaoLoteConjuntoViewSet, basename="movimentacoes-lotes-conjuntos")

urlpatterns = [
    path("", include(router.urls)),
    path("dashboard-integrado/", ProducaoDashboardView.as_view(), name="producao-dashboard-integrado"),
    path("relatorios-integrados/", RelatorioProducaoView.as_view(), name="producao-relatorios-integrados"),
    path("relatorios-lotes-conjuntos/", RelatorioLoteConjuntoView.as_view(), name="producao-relatorios-lotes-conjuntos"),
]

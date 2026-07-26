from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .grain_enterprise_views import (
    AuditoriaProducaoEnterpriseViewSet,
    CadProEnterpriseViewSet,
    ConfiguracaoCulturaViewSet,
    ContratoProducaoEnterpriseViewSet,
    DetalheLocalArmazenagemViewSet,
    EmbarqueProducaoEnterpriseViewSet,
    ImportacaoPlanilhaEnterpriseViewSet,
    MovimentacaoGraosEnterpriseViewSet,
    NotaFiscalProducaoViewSet,
    OrigemTerceiroRecebimentoViewSet,
    RecebimentoProducaoEnterpriseViewSet,
    TransferenciaGraosViewSet,
)
from .grain_views import (
    AcessoCadProViewSet,
    CulturaViewSet,
    MotoristaViewSet,
    ProducaoDashboardView,
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
router.register("configuracoes-cultura", ConfiguracaoCulturaViewSet, basename="configuracoes-cultura")
router.register("safras", SafraViewSet, basename="safras")
router.register("cadpros", CadProEnterpriseViewSet, basename="cadpros")
router.register("acessos-cadpro", AcessoCadProViewSet, basename="acessos-cadpro")
router.register("motoristas", MotoristaViewSet, basename="motoristas")
router.register("veiculos", VeiculoViewSet, basename="veiculos")
router.register("locais-armazenagem", DetalheLocalArmazenagemViewSet, basename="locais-armazenagem-producao")
router.register("contratos", ContratoProducaoEnterpriseViewSet, basename="contratos-producao")
router.register("recebimentos", RecebimentoProducaoEnterpriseViewSet, basename="recebimentos-producao")
router.register("origens-terceiros", OrigemTerceiroRecebimentoViewSet, basename="origens-terceiros-producao")
router.register("embarques", EmbarqueProducaoEnterpriseViewSet, basename="embarques-producao")
router.register("notas-fiscais", NotaFiscalProducaoViewSet, basename="notas-fiscais-producao")
router.register("transferencias", TransferenciaGraosViewSet, basename="transferencias-graos")
router.register("movimentacoes-graos", MovimentacaoGraosEnterpriseViewSet, basename="movimentacoes-graos")
router.register("saldos-graos", SaldoGraosViewSet, basename="saldos-graos")
router.register("auditoria", AuditoriaProducaoEnterpriseViewSet, basename="auditoria-producao")
router.register("importacoes", ImportacaoPlanilhaEnterpriseViewSet, basename="importacoes-producao")

urlpatterns = [
    path("", include(router.urls)),
    path("dashboard-integrado/", ProducaoDashboardView.as_view(), name="producao-dashboard-integrado"),
    path("relatorios-integrados/", RelatorioProducaoView.as_view(), name="producao-relatorios-integrados"),
]

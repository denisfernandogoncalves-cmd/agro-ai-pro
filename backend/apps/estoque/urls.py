from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .compras import CompraEstoqueViewSet
from .disponibilidade import disponibilidade
from .faturamento import FaturamentoInsumoViewSet

from .views import (
    LocalEstoqueViewSet,
    LoteEstoqueViewSet,
    MovimentacaoEstoqueViewSet,
    ProdutoEstoqueViewSet,
)


router = DefaultRouter()
router.register("faturamentos", FaturamentoInsumoViewSet, basename="faturamentos-insumos")
router.register("compras", CompraEstoqueViewSet, basename="compras-estoque")
router.register("produtos", ProdutoEstoqueViewSet, basename="produtos")
router.register("locais", LocalEstoqueViewSet, basename="locais")
router.register("lotes", LoteEstoqueViewSet, basename="lotes")
router.register(
    "movimentacoes",
    MovimentacaoEstoqueViewSet,
    basename="movimentacoes",
)

urlpatterns = [path("disponibilidade/", disponibilidade, name="estoque-disponibilidade"), path("", include(router.urls))]

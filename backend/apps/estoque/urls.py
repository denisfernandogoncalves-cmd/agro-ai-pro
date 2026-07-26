from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    LocalEstoqueViewSet,
    LoteEstoqueViewSet,
    MovimentacaoEstoqueViewSet,
    ProdutoEstoqueViewSet,
)


router = DefaultRouter()
router.register("produtos", ProdutoEstoqueViewSet, basename="produtos")
router.register("locais", LocalEstoqueViewSet, basename="locais")
router.register("lotes", LoteEstoqueViewSet, basename="lotes")
router.register(
    "movimentacoes",
    MovimentacaoEstoqueViewSet,
    basename="movimentacoes",
)

urlpatterns = [path("", include(router.urls))]

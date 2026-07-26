from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CategoriaFinanceiraViewSet,
    CentroCustoViewSet,
    LancamentoFinanceiroViewSet,
    ParceiroFinanceiroViewSet,
)


router = DefaultRouter()
router.register("categorias", CategoriaFinanceiraViewSet, basename="categorias")
router.register("parceiros", ParceiroFinanceiroViewSet, basename="parceiros")
router.register("centros-custo", CentroCustoViewSet, basename="centros-custo")
router.register("lancamentos", LancamentoFinanceiroViewSet, basename="lancamentos")

urlpatterns = [path("", include(router.urls))]

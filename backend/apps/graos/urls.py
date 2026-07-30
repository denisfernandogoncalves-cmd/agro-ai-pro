from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ArmazemGraosViewSet,
    LoteGraosViewSet,
    MovimentacaoGraosViewSet,
)


router = DefaultRouter()
router.register("armazens", ArmazemGraosViewSet, basename="armazens-graos")
router.register("lotes", LoteGraosViewSet, basename="lotes-graos")
router.register(
    "movimentacoes",
    MovimentacaoGraosViewSet,
    basename="movimentacoes-graos",
)

urlpatterns = [path("", include(router.urls))]

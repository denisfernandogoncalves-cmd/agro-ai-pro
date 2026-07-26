from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AbastecimentoMaquinaViewSet,
    MaquinaViewSet,
    ManutencaoMaquinaViewSet,
    UsoMaquinaViewSet,
)


router = DefaultRouter()
router.register("maquinas", MaquinaViewSet, basename="maquinas")
router.register("usos", UsoMaquinaViewSet, basename="usos")
router.register("abastecimentos", AbastecimentoMaquinaViewSet, basename="abastecimentos")
router.register("manutencoes", ManutencaoMaquinaViewSet, basename="manutencoes")

urlpatterns = [path("", include(router.urls))]

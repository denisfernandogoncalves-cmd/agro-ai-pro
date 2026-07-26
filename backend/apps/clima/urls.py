from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AlertaClimaticoViewSet,
    AtualizacaoClimaViewSet,
    ConfiguracaoClimaViewSet,
    PrevisaoClimaViewSet,
    PrevisaoHorariaViewSet,
)


router = DefaultRouter()
router.register("previsoes", PrevisaoClimaViewSet, basename="previsoes")
router.register("horarias", PrevisaoHorariaViewSet, basename="previsoes-horarias")
router.register("alertas", AlertaClimaticoViewSet, basename="alertas-climaticos")
router.register("atualizacoes", AtualizacaoClimaViewSet, basename="atualizacoes-climaticas")
router.register("configuracoes", ConfiguracaoClimaViewSet, basename="configuracoes-climaticas")

urlpatterns = [path("", include(router.urls))]

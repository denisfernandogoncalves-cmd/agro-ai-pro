from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import InsumoOperacaoViewSet, OperacaoAgricolaViewSet


router = DefaultRouter()
router.register("operacoes", OperacaoAgricolaViewSet, basename="operacoes")
router.register("insumos", InsumoOperacaoViewSet, basename="insumos")

urlpatterns = [path("", include(router.urls))]

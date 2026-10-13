from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ReferenciasInvestingViewSet, CotacaoCBOTViewSet, ClimaCornBeltViewSet, CotacaoMercadoViewSet, NoticiaMercadoViewSet


router = DefaultRouter()
router.register("investing", ReferenciasInvestingViewSet, basename="investing")
router.register("cbot", CotacaoCBOTViewSet, basename="cbot")
router.register("cotacoes", CotacaoMercadoViewSet, basename="cotacoes")
router.register("corn-belt", ClimaCornBeltViewSet, basename="corn-belt")
router.register("noticias", NoticiaMercadoViewSet, basename="noticias")

urlpatterns = [path("", include(router.urls))]

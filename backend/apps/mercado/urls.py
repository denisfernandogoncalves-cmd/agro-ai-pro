from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .enterprise_views import (
    AtualizacaoMercadoViewSet,
    ConfiguracaoAtivoMercadoViewSet,
    CotacaoAtivoMercadoViewSet,
)
from .views import ClimaCornBeltViewSet, CotacaoMercadoViewSet, NoticiaMercadoViewSet


router = DefaultRouter()
router.register("cotacoes", CotacaoMercadoViewSet, basename="cotacoes")
router.register("cotacoes-enterprise", CotacaoAtivoMercadoViewSet, basename="cotacoes-enterprise")
router.register("configuracoes-enterprise", ConfiguracaoAtivoMercadoViewSet, basename="configuracoes-enterprise")
router.register("atualizacoes-enterprise", AtualizacaoMercadoViewSet, basename="atualizacoes-enterprise")
router.register("corn-belt", ClimaCornBeltViewSet, basename="corn-belt")
router.register("noticias", NoticiaMercadoViewSet, basename="noticias")

urlpatterns = [path("", include(router.urls))]

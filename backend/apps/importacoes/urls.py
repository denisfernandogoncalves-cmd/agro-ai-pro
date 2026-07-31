from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import LinhaImportacaoViewSet, LoteImportacaoViewSet


router = DefaultRouter()
router.register("lotes", LoteImportacaoViewSet, basename="lotes-importacao")
router.register("linhas", LinhaImportacaoViewSet, basename="linhas-importacao")

urlpatterns = [path("", include(router.urls))]

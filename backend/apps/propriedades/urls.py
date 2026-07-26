from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AcessoPropriedadeViewSet, PropriedadeViewSet


router = DefaultRouter()
router.register("acessos", AcessoPropriedadeViewSet, basename="acesso-propriedade")
router.register("", PropriedadeViewSet, basename="propriedade")

urlpatterns = [path("", include(router.urls))]

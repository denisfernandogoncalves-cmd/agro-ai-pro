from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import VendaGraosViewSet


router = DefaultRouter()
router.register("vendas", VendaGraosViewSet, basename="vendas-graos")

urlpatterns = [path("", include(router.urls))]


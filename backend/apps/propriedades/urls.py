from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import PropriedadeViewSet


router = DefaultRouter()

router.register(
    "",
    PropriedadeViewSet,
    basename="propriedade"
)


urlpatterns = [
    path("", include(router.urls)),
]
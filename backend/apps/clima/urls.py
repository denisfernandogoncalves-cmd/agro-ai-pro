from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PrevisaoClimaViewSet


router = DefaultRouter()

router.register(
    "previsoes",
    PrevisaoClimaViewSet,
    basename="previsoes"
)


urlpatterns = [
    path("", include(router.urls)),
]
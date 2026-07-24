from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TalhaoViewSet


router = DefaultRouter()

router.register(
    "talhoes",
    TalhaoViewSet,
    basename="talhao"
)


urlpatterns = [
    path("", include(router.urls)),
]
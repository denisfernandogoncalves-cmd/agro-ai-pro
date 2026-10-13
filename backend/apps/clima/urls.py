from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PrevisaoClimaViewSet
from .satelite import SateliteView


router = DefaultRouter()

router.register(
    "previsoes",
    PrevisaoClimaViewSet,
    basename="previsoes"
)


urlpatterns = [
    path("satelite/", SateliteView.as_view(), name="satelite"),
    path("", include(router.urls)),
]
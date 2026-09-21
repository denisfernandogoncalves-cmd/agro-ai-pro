from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import HistoricoAgronomicoViewSet, TalhaoViewSet
from .grupos import GrupoPropriedadesViewSet


router = DefaultRouter()
router.register("grupos-colheita", GrupoPropriedadesViewSet, basename="grupo-propriedades-colheita")

router.register(
    "talhoes",
    TalhaoViewSet,
    basename="talhao"
)
router.register(
    "historicos-agronomicos",
    HistoricoAgronomicoViewSet,
    basename="historico-agronomico",
)


urlpatterns = [
    path("", include(router.urls)),
]

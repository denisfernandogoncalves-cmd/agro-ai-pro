from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import HistoricoAgronomicoViewSet, TalhaoViewSet


router = DefaultRouter()
router.register("talhoes", TalhaoViewSet, basename="talhao")
router.register(
    "historicos-agronomicos",
    HistoricoAgronomicoViewSet,
    basename="historico-agronomico",
)

talhoes_lista = TalhaoViewSet.as_view({"get": "list", "post": "create"})

urlpatterns = [
    path("", talhoes_lista, name="talhoes-lista-compatibilidade"),
    path("", include(router.urls)),
]

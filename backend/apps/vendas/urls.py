from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ContratoComercialViewSet, VendaGraosViewSet


router = DefaultRouter()
router.register("contratos", ContratoComercialViewSet, basename="contratos-comerciais")
router.register("vendas", VendaGraosViewSet, basename="vendas-graos")

from .acerto import AcertoView
from .consulta_romaneios import ConsultaRomaneiosSaidaView

urlpatterns = [path("romaneios/", ConsultaRomaneiosSaidaView.as_view(), name="consulta-romaneios-saida"), path("acertos/", AcertoView.as_view()), path("acertos/<int:pk>/", AcertoView.as_view()), path("", include(router.urls))]

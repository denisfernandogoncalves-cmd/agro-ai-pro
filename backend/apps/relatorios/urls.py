from django.urls import path

from .views import (
    DashboardGerencialView,
    OpcoesRelatorioOperacionalView,
    RelatorioOperacionalView,
)

urlpatterns = [
    path("dashboard/", DashboardGerencialView.as_view(), name="dashboard"),
    path("operacionais/", RelatorioOperacionalView.as_view(), name="operacionais"),
    path(
        "operacionais/opcoes/",
        OpcoesRelatorioOperacionalView.as_view(),
        name="operacionais-opcoes",
    ),
]

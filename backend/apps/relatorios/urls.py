from django.urls import path
from .excel import RelatorioExcelView

from .views import (
    DashboardGerencialView,
    OpcoesRelatorioOperacionalView,
    RelatorioOperacionalView,
)

urlpatterns = [
    path("operacionais/exportar/", RelatorioExcelView.as_view(), name="relatorio-excel"),
    path("dashboard/", DashboardGerencialView.as_view(), name="dashboard"),
    path("operacionais/", RelatorioOperacionalView.as_view(), name="operacionais"),
    path(
        "operacionais/opcoes/",
        OpcoesRelatorioOperacionalView.as_view(),
        name="operacionais-opcoes",
    ),
]

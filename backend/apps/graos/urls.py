from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ArmazemGraosViewSet,
    CargaColhidaViewSet,
    LoteGraosViewSet,
    MovimentacaoGraosViewSet,
    OrigemSaldoGraosViewSet,
    ReservaSaldoGraosViewSet,
    SaldoGraosViewSet,
)


router = DefaultRouter()
router.register("armazens", ArmazemGraosViewSet, basename="armazens-graos")
router.register("cargas-colhidas", CargaColhidaViewSet, basename="cargas-colhidas")
router.register("lotes", LoteGraosViewSet, basename="lotes-graos")
router.register(
    "movimentacoes",
    MovimentacaoGraosViewSet,
    basename="movimentacoes-graos",
)
router.register("saldos", SaldoGraosViewSet, basename="saldos-graos")
router.register("origens-saldo", OrigemSaldoGraosViewSet, basename="origens-saldo-graos")
router.register("reservas", ReservaSaldoGraosViewSet, basename="reservas-saldo-graos")

from .transferencias_correcoes import CorrecaoTransferenciaView

urlpatterns = [
    path("transferencias/<int:pk>/", CorrecaoTransferenciaView.as_view(), name="correcao-transferencia-saldo"),
    path(
        "producoes/creditar/",
        SaldoGraosViewSet.as_view({"post": "creditar_producao"}),
        name="graos-producoes-creditar",
    ),
    path(
        "ajustes/",
        SaldoGraosViewSet.as_view({"post": "registrar_ajuste"}),
        name="graos-ajustes",
    ),
    path(
        "transferencias/",
        SaldoGraosViewSet.as_view({"post": "transferir"}),
        name="graos-transferencias",
    ),
    path("", include(router.urls)),
]

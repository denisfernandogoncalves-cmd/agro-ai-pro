from django.urls import path
from .views import ContextoOfflineView, SincronizarCargaView, SnapshotCargaView

urlpatterns = [
    path("contexto/", ContextoOfflineView.as_view(), name="offline-contexto"),
    path("cargas/", SincronizarCargaView.as_view(), name="offline-cargas"),
    path("cargas/<int:pk>/", SnapshotCargaView.as_view(), name="offline-carga-snapshot"),
]

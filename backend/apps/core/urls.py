from django.urls import path
from .views import PainelView, FavoritosView, FavoritoDetailView, HistoricoView

from .rascunhos import RascunhoView
from .conferencia import ConferenciaView, EstornoConferidoView, SimularVendaView

urlpatterns = [
    path("simular-venda/", SimularVendaView.as_view(), name="simular-venda"),
    path("conferencia/movimentos/<int:pk>/estornar/", EstornoConferidoView.as_view(), name="estorno-conferido"),
    path("rascunhos/<str:contexto>/", RascunhoView.as_view(), name="rascunho-formulario"),
    path("conferencia/<int:pk>/", ConferenciaView.as_view(), name="conferencia-saldo"),
    path("painel/", PainelView.as_view(), name="painel-inicial"),
    path("favoritos/", FavoritosView.as_view(), name="filtros-favoritos"),
    path("favoritos/<int:pk>/", FavoritoDetailView.as_view(), name="filtro-favorito-detalhe"),
    path("historico/", HistoricoView.as_view(), name="historico-alteracoes"),
]

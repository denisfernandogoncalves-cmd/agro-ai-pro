from django.urls import path
from .views import PainelView, FavoritosView, FavoritoDetailView, HistoricoView

from .rascunhos import RascunhoView
from .conferencia import ConferenciaView, EstornoConferidoView, SimularVendaView
from .excel import BackupExcelView
from .anexos import AnexosView, AnexoDetailView
from .duplicidades import DuplicidadesView

urlpatterns = [
    path("duplicidades/<str:entidade>/", DuplicidadesView.as_view(), name="duplicidades"),
    path("backup-excel/", BackupExcelView.as_view(), name="backup-excel"),
    path("anexos/arquivo/<int:pk>/", AnexoDetailView.as_view(), name="anexo-arquivo"),
    path("anexos/<str:entidade>/<str:registro_id>/", AnexosView.as_view(), name="anexos-lancamento"),
    path("simular-venda/", SimularVendaView.as_view(), name="simular-venda"),
    path("conferencia/movimentos/<int:pk>/estornar/", EstornoConferidoView.as_view(), name="estorno-conferido"),
    path("rascunhos/<str:contexto>/", RascunhoView.as_view(), name="rascunho-formulario"),
    path("conferencia/<int:pk>/", ConferenciaView.as_view(), name="conferencia-saldo"),
    path("painel/", PainelView.as_view(), name="painel-inicial"),
    path("favoritos/", FavoritosView.as_view(), name="filtros-favoritos"),
    path("favoritos/<int:pk>/", FavoritoDetailView.as_view(), name="filtro-favorito-detalhe"),
    path("historico/", HistoricoView.as_view(), name="historico-alteracoes"),
]

from django.urls import path
from .views import PainelView, FavoritosView, FavoritoDetailView, HistoricoView

from .rascunhos import RascunhoView
from .conferencia import ConferenciaView, EstornoConferidoView, SimularVendaView
from .excel import BackupExcelView
from .anexos import AnexosView, AnexoDetailView
from .duplicidades import DuplicidadesView
from .backup_status import BackupStatusView
from apps.graos.conferencia_estoque import ConferenciaEstoqueView
from apps.graos.fechamentos import FechamentosView
from apps.graos.pendencias import PendenciasView

urlpatterns = [
    path("fechamentos/", FechamentosView.as_view(), name="fechamentos"),
    path("pendencias-conferencia/", PendenciasView.as_view(), name="pendencias-conferencia"),
    path("pendencias-conferencia/<int:pk>/", PendenciasView.as_view(), name="pendencia-conferencia-detalhe"),
    path("conferencia-estoque/previa/", ConferenciaEstoqueView.as_view(previa=True), name="conferencia-estoque-previa"),
    path("conferencia-estoque/", ConferenciaEstoqueView.as_view(), name="conferencia-estoque"),
    path("backup-status/", BackupStatusView.as_view(), name="backup-status"),
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

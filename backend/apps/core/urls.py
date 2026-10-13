from django.urls import path
from .views import PainelView, FavoritosView, FavoritoDetailView, HistoricoView

from .rascunhos import RascunhoView
from .conferencia import ConferenciaView, EstornoConferidoView, SimularVendaView
from .excel import BackupExcelView
from .anexos import AnexosView, AnexoDetailView
from .duplicidades import DuplicidadesView
from .backup_status import BackupStatusView
from .central_gestao import DiagnosticoView, DocumentosView, ConferenciaFinanceiraView
from .revisao_gestao import ChecklistSafraView, ExtratoCadproView, ComparacaoSafrasView
from .origem_pendencia import OrigemPendenciaView
from apps.graos.conferencia_estoque import ConferenciaEstoqueView
from apps.graos.fechamentos import FechamentosView
from apps.graos.pendencias import PendenciasView

from .conferencia_diaria import ConferenciaDiariaView

urlpatterns = [
    path("conferencia-diaria/", ConferenciaDiariaView.as_view(), name="conferencia-diaria"),
    path("pendencias-conferencia/<int:pk>/origem/", OrigemPendenciaView.as_view(), name="origem-pendencia"),
    path("checklist-safra/", ChecklistSafraView.as_view(), name="checklist-safra"),
    path("extrato-cadpro/", ExtratoCadproView.as_view(), name="extrato-cadpro"),
    path("comparacao-safras/", ComparacaoSafrasView.as_view(), name="comparacao-safras"),
    path("diagnostico/", DiagnosticoView.as_view(), name="diagnostico"),
    path("documentos/", DocumentosView.as_view(), name="central-documentos"),
    path("conferencia-financeira/", ConferenciaFinanceiraView.as_view(), name="conferencia-financeira"),
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

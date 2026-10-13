from types import SimpleNamespace
from django.test import SimpleTestCase
from .confirmation_services import _validar_lote, ConfirmacaoImportacaoError
from .models import LoteImportacao


class HistoricoInsumosTests(SimpleTestCase):
    def test_historico_nao_pode_ser_confirmado_como_graos(self):
        lote = LoteImportacao(status=LoteImportacao.Status.HISTORICO, total_erros=0)
        with self.assertRaises(ConfirmacaoImportacaoError) as erro:
            _validar_lote(lote, [SimpleNamespace(erros=[])])
        self.assertEqual(erro.exception.codigo, 'lote_nao_elegivel')

    def test_historico_aceito_pelo_campo_sem_marcar_confirmado(self):
        campo = LoteImportacao._meta.get_field('status')
        self.assertEqual(campo.clean('historico', LoteImportacao()), 'historico')
        self.assertNotEqual(LoteImportacao.Status.HISTORICO, LoteImportacao.Status.CONFIRMADO)

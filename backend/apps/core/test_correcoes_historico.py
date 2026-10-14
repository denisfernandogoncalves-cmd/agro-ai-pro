from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from apps.accounts.models import AcessoUsuario
from apps.core.models import RegistroAlteracao
from apps.producao.tests import OperacaoBase
from apps.producao.models import InsumoOperacao
from apps.producao.services import iniciar_operacao, concluir_operacao
from apps.estoque.services import registrar_movimentacao, saldo_lote
from apps.maquinas.tests import MaquinaBase
from apps.maquinas.models import UsoMaquina
from apps.transportes.test_fretes import FretesCargasTests


def payload(dado, **campos):
    return {"versao_correcao_original": dado["versao_correcao"], "motivo_correcao": "Corrigir lançamento conferido", **campos}


class EstoqueCorrecaoTests(OperacaoBase, TestCase):
    def setUp(self):
        self.criar_dados()
        self.client = APIClient(); self.client.force_authenticate(self.usuario)
        self.entrada = self.lote.movimentacoes.get(tipo="entrada")
        self.url = f"/api/estoque/movimentacoes/{self.entrada.pk}/"

    def test_corrige_com_original_e_impede_resposta_obsoleta(self):
        dado = self.client.get(self.url).data
        resposta = self.client.patch(self.url + "corrigir/", payload(dado, quantidade="600"), format="json")
        self.assertEqual(resposta.status_code, 200, resposta.data)
        self.assertEqual(saldo_lote(self.lote), Decimal("600"))
        evento = RegistroAlteracao.objects.get(acao="corrigir", modulo="estoque")
        self.assertEqual(Decimal(evento.alteracoes["registro_original"]["antes"]["quantidade"]), Decimal("500"))
        self.assertEqual(self.client.patch(self.url + "corrigir/", payload(dado, quantidade="700"), format="json").status_code, 409)

    def test_saldo_negativo_reverte_tudo_e_cancelamento_preserva_original(self):
        saida = registrar_movimentacao(usuario=self.usuario, tipo="saida", lote=self.lote, quantidade="400")
        dado = self.client.get(self.url).data
        self.assertEqual(self.client.patch(self.url + "corrigir/", payload(dado, quantidade="300"), format="json").status_code, 400)
        self.assertEqual(saldo_lote(self.lote), Decimal("100"))
        self.assertFalse(RegistroAlteracao.objects.filter(acao="corrigir").exists())
        self.assertEqual(self.client.delete(self.url + "cancelar-registro/", payload(dado), format="json").status_code, 400)
        url = f"/api/estoque/movimentacoes/{saida.pk}/"
        saida_dado = self.client.get(url).data
        self.assertEqual(self.client.delete(url + "cancelar-registro/", payload(saida_dado), format="json").status_code, 204)
        self.assertEqual(saldo_lote(self.lote), Decimal("500"))
        self.assertTrue(RegistroAlteracao.objects.filter(acao="cancelar", registro_id=str(saida_dado["id"])).exists())

    def test_motivo_e_permissoes(self):
        dado = self.client.get(self.url).data
        self.assertEqual(self.client.patch(self.url + "corrigir/", payload(dado, quantidade="600", motivo_correcao=""), format="json").status_code, 400)
        AcessoUsuario.objects.create(usuario=self.usuario, modulos=["estoque"], permissoes={"estoque": ["consultar"]})
        self.assertEqual(self.client.patch(self.url + "corrigir/", payload(dado, quantidade="600"), format="json").status_code, 403)
        self.assertEqual(self.client.delete(self.url + "cancelar-registro/", payload(dado), format="json").status_code, 403)


class OperacaoCorrecaoTests(OperacaoBase, TestCase):
    def setUp(self):
        self.criar_dados()
        self.client = APIClient(); self.client.force_authenticate(self.usuario)
        self.insumo = InsumoOperacao.objects.create(operacao=self.operacao, lote=self.lote, quantidade_planejada="50")
        self.operacao = iniciar_operacao(self.operacao)
        self.operacao = concluir_operacao(self.operacao, usuario=self.usuario, custo_realizado="100")
        self.url = f"/api/producao/operacoes/{self.operacao.pk}/"

    def test_corrige_custo_e_cancela_concluida_estornando_consumo(self):
        dado = self.client.get(self.url).data
        r = self.client.patch(self.url + "corrigir/", payload(dado, custo_realizado="200"), format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(saldo_lote(self.lote), Decimal("450"))
        r = self.client.delete(self.url + "cancelar-registro/", payload(r.data), format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["status"], "cancelada")
        self.assertEqual(saldo_lote(self.lote), Decimal("500"))
        self.insumo.refresh_from_db(); self.assertIsNone(self.insumo.movimentacao_estoque_id)
        self.assertEqual(RegistroAlteracao.objects.filter(acao__in=["corrigir", "cancelar"]).count(), 2)

    def test_movimento_vinculado_nao_e_corrigido_isoladamente(self):
        self.insumo.refresh_from_db()
        url = f"/api/estoque/movimentacoes/{self.insumo.movimentacao_estoque_id}/"
        dado = self.client.get(url).data
        self.assertEqual(self.client.patch(url + "corrigir/", payload(dado, quantidade="70"), format="json").status_code, 400)
        self.assertEqual(saldo_lote(self.lote), Decimal("450"))

    def test_corrige_e_cancela_insumo_encerrado_com_saldo_e_original(self):
        url = f"/api/producao/insumos/{self.insumo.pk}/"
        dado = self.client.get(url).data
        r = self.client.patch(url + "corrigir/", payload(dado, quantidade_utilizada="80"), format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(saldo_lote(self.lote), Decimal("420"))
        invalido = self.client.patch(url + "corrigir/", payload(r.data, quantidade_utilizada="600"), format="json")
        self.assertEqual(invalido.status_code, 400)
        self.assertEqual(saldo_lote(self.lote), Decimal("420"))
        r = self.client.delete(url + "cancelar-registro/", payload(r.data), format="json")
        self.assertEqual(r.status_code, 204, getattr(r, "data", None))
        self.assertEqual(saldo_lote(self.lote), Decimal("500"))


class MaquinaCorrecaoTests(MaquinaBase, TestCase):
    def setUp(self):
        self.criar_dados()
        self.client = APIClient(); self.client.force_authenticate(self.usuario)
        self.uso = UsoMaquina.objects.create(maquina=self.maquina, operacao=self.operacao, horimetro_inicial="100", horimetro_final="105")
        self.maquina.horimetro_atual = Decimal("105"); self.maquina.save()
        self.url = f"/api/maquinas/usos/{self.uso.pk}/"

    def test_corrige_e_cancela_com_horimetro_confirmado_e_original(self):
        dado = self.client.get(self.url).data
        r = self.client.patch(self.url + "corrigir/", payload(dado, horimetro_final="106", horimetro_corrigido="106", versao_maquina_original=dado["versao_maquina_original"]), format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.maquina.refresh_from_db(); self.assertEqual(self.maquina.horimetro_atual, Decimal("106"))
        dado = self.client.get(self.url).data
        r = self.client.delete(self.url + "cancelar-registro/", payload(dado, horimetro_corrigido="100", versao_maquina_original=dado["versao_maquina_original"]), format="json")
        self.assertEqual(r.status_code, 204, getattr(r, "data", None))
        self.maquina.refresh_from_db(); self.assertEqual(self.maquina.horimetro_atual, Decimal("100"))
        self.assertFalse(UsoMaquina.objects.filter(pk=self.uso.pk).exists())
        evento = RegistroAlteracao.objects.get(acao="cancelar")
        self.assertEqual(Decimal(evento.alteracoes["registro_original"]["antes"]["horimetro_final"]), Decimal("106"))

    def test_leitura_menor_que_historico_reverte_correcao(self):
        dado = self.client.get(self.url).data
        r = self.client.patch(self.url + "corrigir/", payload(dado, operador="Novo", horimetro_corrigido="99", versao_maquina_original=dado["versao_maquina_original"]), format="json")
        self.assertEqual(r.status_code, 400)
        self.uso.refresh_from_db(); self.assertEqual(self.uso.operador, "")
        self.assertFalse(RegistroAlteracao.objects.filter(acao="corrigir").exists())

    def test_uso_sobreposto_e_maquina_alterada_nao_sao_sobrescritos(self):
        dado = self.client.get(self.url).data
        self.maquina.horimetro_atual = Decimal("110"); self.maquina.save()
        r = self.client.patch(self.url + "corrigir/", payload(dado, operador="Novo", horimetro_corrigido="110", versao_maquina_original=dado["versao_maquina_original"]), format="json")
        self.assertEqual(r.status_code, 400)
        UsoMaquina.objects.create(maquina=self.maquina, operacao=self.operacao, horimetro_inicial="106", horimetro_final="110")
        dado = self.client.get(self.url).data
        r = self.client.patch(self.url + "corrigir/", payload(dado, horimetro_final="107", horimetro_corrigido="110", versao_maquina_original=dado["versao_maquina_original"]), format="json")
        self.assertEqual(r.status_code, 400)
        self.uso.refresh_from_db(); self.assertEqual(self.uso.horimetro_final, Decimal("105"))

    def test_cancelar_manutencao_concluida_preserva_custo_original(self):
        dado = self.client.post("/api/maquinas/manutencoes/", {"maquina": self.maquina.pk, "descricao": "Revisão", "data_prevista": "2026-01-01"}, format="json").data
        url = f"/api/maquinas/manutencoes/{dado['id']}/"
        r = self.client.post(url + "concluir/", {"data_conclusao": "2026-01-01", "horimetro_realizado": "120", "custo": "50"}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        dado = self.client.get(url).data
        r = self.client.delete(url + "cancelar-registro/", payload(dado, horimetro_corrigido="105", versao_maquina_original=dado["versao_maquina_original"]), format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["custo"], "0.00")
        self.assertEqual(r.data["status"], "cancelada")
        self.assertEqual(RegistroAlteracao.objects.get(acao="cancelar").alteracoes["registro_original"]["antes"]["custo"], "50.00")


class FreteCorrecaoTests(FretesCargasTests):
    def test_corrigir_comissao_manual_nao_duplica_fretes(self):
        self.client.post(self.url, self.dados, format="json")
        url = f"/api/transportes/remuneracoes/{self.rem.pk}/"
        dado = self.client.get(url).data
        self.assertEqual(dado["comissao_manual"], "50.00")
        resposta = self.client.patch(url + "corrigir/", payload(dado, comissao_manual="60"), format="json")
        self.assertEqual(resposta.status_code, 200, resposta.data)
        self.assertEqual(resposta.data["comissao"], "160.00")
        self.assertEqual(RegistroAlteracao.objects.get(acao="corrigir").alteracoes["registro_original"]["antes"]["comissao"], "50.00")

    def test_cancelamento_retira_comissao_e_preserva_original(self):
        dado = self.client.post(self.url, self.dados, format="json").data
        r = self.client.delete(f"{self.url}{dado['id']}/cancelar-registro/", payload(dado), format="json")
        self.assertEqual(r.status_code, 204, getattr(r, "data", None))
        self.assertEqual(self.rem.valor_comissao, Decimal("50.00"))
        self.assertEqual(RegistroAlteracao.objects.get(acao="cancelar").alteracoes["registro_original"]["antes"]["comissao"], "100.00")

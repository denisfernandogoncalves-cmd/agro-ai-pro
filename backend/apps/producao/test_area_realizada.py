from decimal import Decimal
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from apps.estoque.services import saldo_lote
from apps.relatorios.selectors import _operacoes_agricolas
from .tests import OperacaoBase
from .models import InsumoOperacao, OperacaoAgricola
from .services import iniciar_operacao, concluir_operacao, TransicaoOperacaoError


class AreaRealizadaTests(OperacaoBase, TestCase):
    def setUp(self):
        self.criar_dados()
        iniciar_operacao(self.operacao)

    def test_ausencia_nao_copia_planejada_nem_inventa_zero(self):
        concluida=concluir_operacao(self.operacao,usuario=self.usuario)
        self.assertIsNone(concluida.area_realizada_hectares)
        linha=_operacoes_agricolas({"propriedade":self.propriedade.pk})[0]
        self.assertIsNone(linha["area_realizada_hectares"])
        self.assertIsNone(linha["comparacao"]["area_diferenca_hectares"])

    def test_area_registrada_nao_altera_area_planejada_ou_talhao(self):
        concluida=concluir_operacao(self.operacao,usuario=self.usuario,area_realizada_hectares="30.25",custo_realizado="2300")
        self.assertEqual(concluida.area_hectares,Decimal("40"))
        self.assertEqual(concluida.area_realizada_hectares,Decimal("30.25"))
        self.talhao.refresh_from_db();self.assertEqual(self.talhao.area_hectares,Decimal("40"))
        linha=_operacoes_agricolas({"propriedade":self.propriedade.pk})[0]
        self.assertEqual(Decimal(linha["comparacao"]["area_diferenca_hectares"]),Decimal("-9.75"))
        self.assertEqual(Decimal(linha["area_realizada_hectares"]),Decimal("30.25"))

    def test_realizado_acima_do_planejado_dentro_do_talhao_explicita_diferenca(self):
        self.operacao.refresh_from_db()
        self.operacao.area_hectares=Decimal("30");self.operacao.save(update_fields=["area_hectares"])
        concluir_operacao(self.operacao,usuario=self.usuario,area_realizada_hectares="35")
        linha=_operacoes_agricolas({"propriedade":self.propriedade.pk})[0]
        self.assertEqual(Decimal(linha["area_diferenca_hectares"]),Decimal("5"))

    def test_valores_invalidos_e_limite_preservam_operacao_e_estoque(self):
        InsumoOperacao.objects.create(operacao=self.operacao,lote=self.lote,quantidade_planejada="100")
        for valor in ["NaN","Infinity","-1","0","1.001","1000000000","40.01"]:
            with self.subTest(valor=valor):
                with self.assertRaises((ValueError,ValidationError)):
                    concluir_operacao(self.operacao,usuario=self.usuario,area_realizada_hectares=valor)
                self.operacao.refresh_from_db()
                self.assertEqual(self.operacao.status,"em_execucao")
                self.assertIsNone(self.operacao.area_realizada_hectares)
                self.assertEqual(saldo_lote(self.lote),Decimal("500"))
                self.assertIsNone(self.operacao.insumos.get().movimentacao_estoque_id)

    def test_reenvio_nao_repete_consumo_nem_altera_area(self):
        InsumoOperacao.objects.create(operacao=self.operacao,lote=self.lote,quantidade_planejada="100")
        concluir_operacao(self.operacao,usuario=self.usuario,area_realizada_hectares="30")
        with self.assertRaises(TransicaoOperacaoError):
            concluir_operacao(self.operacao,usuario=self.usuario,area_realizada_hectares="20")
        self.operacao.refresh_from_db()
        self.assertEqual(self.operacao.area_realizada_hectares,Decimal("30"))
        self.assertEqual(saldo_lote(self.lote),Decimal("400"))


class AreaRealizadaAPITests(OperacaoBase, APITestCase):
    def setUp(self):
        self.criar_dados()
        self.client.credentials(HTTP_AUTHORIZATION="Bearer "+str(RefreshToken.for_user(self.usuario).access_token))
        iniciar_operacao(self.operacao)

    def test_conclusao_api_e_correcao_versionada_com_historico(self):
        resposta=self.client.post(f"/api/producao/operacoes/{self.operacao.pk}/concluir/",{"area_realizada_hectares":"25.00"},format="json")
        self.assertEqual(resposta.status_code,200,resposta.data)
        self.assertEqual(Decimal(resposta.data["area_realizada_hectares"]),Decimal("25"))
        payload={"area_realizada_hectares":"24.00","motivo_correcao":"Conferência da área executada","versao_correcao_original":resposta.data["versao_correcao"]}
        corrigida=self.client.patch(f"/api/producao/operacoes/{self.operacao.pk}/corrigir/",payload,format="json")
        self.assertEqual(corrigida.status_code,200,corrigida.data)
        antiga=self.client.patch(f"/api/producao/operacoes/{self.operacao.pk}/corrigir/",payload,format="json")
        self.assertEqual(antiga.status_code,409)
        from apps.core.models import RegistroAlteracao
        registro=RegistroAlteracao.objects.filter(modulo="operacoes",acao="corrigir").latest("id")
        self.assertEqual(Decimal(registro.alteracoes["registro_original"]["antes"]["area_realizada_hectares"]),Decimal("25"))
        self.assertEqual(Decimal(registro.alteracoes["registro_original"]["depois"]["area_realizada_hectares"]),Decimal("24"))

    def test_consultor_nao_conclui_nem_corrige(self):
        from apps.accounts.models import AcessoUsuario
        AcessoUsuario.objects.update_or_create(usuario=self.usuario,defaults={"modulos":["operacoes"],"permissoes":{"operacoes":["consultar"]}})
        resposta=self.client.post(f"/api/producao/operacoes/{self.operacao.pk}/concluir/",{"area_realizada_hectares":"20"},format="json")
        self.assertEqual(resposta.status_code,403)
        self.operacao.refresh_from_db();self.assertIsNone(self.operacao.area_realizada_hectares)

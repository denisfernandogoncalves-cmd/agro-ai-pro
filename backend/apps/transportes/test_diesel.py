from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import AcessoUsuario
from apps.maquinas.models import CompraDiesel
from .models import Caminhao, LancamentoTransporte


class DieselTests(APITestCase):
    compras = "/api/transportes/compras-diesel/"
    lancamentos = "/api/transportes/lancamentos/"

    def setUp(self):
        self.usuario = get_user_model().objects.create_user("diesel", password="test")
        AcessoUsuario.objects.create(usuario=self.usuario, modulos=["transportes"])
        token = RefreshToken.for_user(self.usuario)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
        self.caminhao = Caminhao.objects.create(placa="ABC1D23", veiculo="Caminhão", motorista="João")
        self.compra = CompraDiesel.objects.create(data="2026-10-06", fornecedor="GP", produtor="NEI", tipo="S10", litros="6000", valor_unitario="7.12", prazo_dias=15)

    def dados(self, **alteracoes):
        return dict(caminhao=self.caminhao.pk, motorista="João", data="2026-10-10", tipo="despesa", descricao="Diesel no silo", quantidade="100", abasteceu_silo=True, tipo_diesel="S10", **alteracoes)

    def test_compra_total_vencimento_filtros_resumo(self):
        CompraDiesel.objects.create(data="2026-10-08", fornecedor="Outro", produtor="Outro", tipo="S500", litros="6000", valor_unitario="7.09")
        resposta = self.client.get(self.compras, {"tipo": "S10", "fornecedor": "gp", "data_inicio": "2026-10-01", "data_fim": "2026-10-07", "page": 1})
        self.assertEqual(resposta.status_code, 200, resposta.data)
        self.assertEqual(resposta.data["count"], 1)
        self.assertEqual(resposta.data["results"][0]["valor_total"], "42720.00")
        self.assertEqual(resposta.data["results"][0]["vencimento"], "2026-10-21")
        resumo = self.client.get(self.compras + "resumo/", {"tipo": "S10"}).data
        self.assertEqual(Decimal(resumo["litros"]), Decimal("6000"))
        self.assertEqual(Decimal(resumo["valor_total"]), Decimal("42720"))
        for params in ({"data_inicio": "inválida"}, {"data_inicio": "2026-10-10", "data_fim": "2026-10-01"}, {"tipo": "outro"}):
            self.assertEqual(self.client.get(self.compras, params).status_code, 400)

    def test_preco_ultima_compra_sem_futuro_nem_outro_tipo(self):
        CompraDiesel.objects.create(data="2026-10-11", fornecedor="GP", produtor="NEI", tipo="S10", litros="10", valor_unitario="9")
        CompraDiesel.objects.create(data="2026-10-09", fornecedor="GP", produtor="NEI", tipo="S500", litros="10", valor_unitario="8")
        resposta = self.client.get(self.lancamentos + "preco-silo/", {"data": "2026-10-10", "tipo_diesel": "S10"})
        self.assertEqual(resposta.status_code, 200, resposta.data)
        self.assertEqual(resposta.data["compra"], self.compra.pk)
        dados = self.dados(valor_unitario="0.0001", unidade="un")
        resposta = self.client.post(self.lancamentos, dados, format="json")
        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.assertEqual(resposta.data["total"], "712.00")
        self.assertEqual(resposta.data["unidade"], "L")
        self.assertEqual(resposta.data["compra_diesel"], self.compra.pk)

    def test_sem_compra_bloqueia_despesa_e_receita_invalida(self):
        dados = self.dados()
        dados["data"] = "2026-10-05"
        self.assertEqual(self.client.post(self.lancamentos, dados, format="json").status_code, 400)
        dados["data"] = "2026-10-10"
        dados["tipo"] = "receita"
        self.assertEqual(self.client.post(self.lancamentos, dados, format="json").status_code, 400)
        self.assertFalse(LancamentoTransporte.objects.exists())

    def test_snapshot_e_edicao_versionada(self):
        criada = self.client.post(self.lancamentos, self.dados(), format="json")
        self.assertEqual(criada.status_code, 201, criada.data)
        self.compra.valor_unitario = Decimal("8")
        self.compra.save()
        url = self.lancamentos + str(criada.data["id"]) + "/"
        editada = self.client.patch(url, {"quantidade": "200", "valor_unitario": "1", "versao_correcao_original": criada.data["versao_correcao"]}, format="json")
        self.assertEqual(editada.status_code, 200, editada.data)
        self.assertEqual(editada.data["total"], "1424.00")
        self.assertEqual(self.client.patch(url, {"quantidade": "300", "versao_correcao_original": criada.data["versao_correcao"]}, format="json").status_code, 409)
        editada = self.client.patch(url, {"data": "2026-10-11", "versao_correcao_original": editada.data["versao_correcao"]}, format="json")
        self.assertEqual(editada.status_code, 200, editada.data)
        self.assertEqual(editada.data["total"], "1600.00")

    def test_permissoes_reais(self):
        self.client.credentials()
        self.assertEqual(self.client.get(self.compras).status_code, 401)
        acesso = AcessoUsuario.objects.get(usuario=self.usuario)
        acesso.modulos = ["mercado"]
        acesso.save()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(self.usuario).access_token}")
        self.assertEqual(self.client.get(self.compras).status_code, 403)

    def test_validacao_compra_e_edicao(self):
        dados = {"data": "2026-10-12", "fornecedor": "GP", "produtor": "NEI", "tipo": "S10", "litros": "0", "valor_unitario": "7"}
        self.assertEqual(self.client.post(self.compras, dados, format="json").status_code, 400)
        dados["litros"] = "10"
        criada = self.client.post(self.compras, dados, format="json")
        self.assertEqual(criada.status_code, 201, criada.data)
        from apps.core.models import RegistroAlteracao
        self.assertTrue(RegistroAlteracao.objects.filter(modulo="transportes", registro_id=str(criada.data["id"]), alteracoes__has_key="fornecedor").exists())
        self.assertIsNone(criada.data["vencimento"])
        url = self.compras + str(criada.data["id"]) + "/"
        self.assertEqual(self.client.patch(url, {"litros": "11"}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(url, {"litros": "11", "atualizado_em_original": criada.data["atualizado_em"]}, format="json").status_code, 200)

    def test_despesa_manual_preservada(self):
        dados = self.dados(valor_unitario="5")
        dados["abasteceu_silo"] = False
        resposta = self.client.post(self.lancamentos, dados, format="json")
        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.assertEqual(resposta.data["total"], "500.00")
        self.assertIsNone(resposta.data["compra_diesel"])

    def test_preco_previa_alterado_bloqueia_salvamento(self):
        dados = self.dados(compra_diesel_esperada=self.compra.pk, preco_diesel_esperado="6")
        self.assertEqual(self.client.post(self.lancamentos, dados, format="json").status_code, 400)
        self.assertFalse(LancamentoTransporte.objects.exists())

    def test_mesmo_dia_usa_ultima_compra_registrada(self):
        ultima = CompraDiesel.objects.create(data="2026-10-06", fornecedor="GP", produtor="NEI", tipo="S10", litros="100", valor_unitario="7.5")
        dados = self.dados()
        dados["data"] = "2026-10-06"
        resposta = self.client.post(self.lancamentos, dados, format="json")
        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.assertEqual(resposta.data["compra_diesel"], ultima.pk)
        self.assertEqual(resposta.data["total"], "750.00")

    def test_exclusao_versionada_preserva_compra_abastecimento_e_auditoria(self):
        criada = self.client.post(self.lancamentos, self.dados(), format='json')
        self.assertEqual(criada.status_code, 201)
        url = self.compras + str(self.compra.pk) + '/'
        versao = self.client.get(url).data['atualizado_em']
        self.assertEqual(self.client.delete(url, {}, format='json').status_code, 400)
        self.assertEqual(self.client.delete(url, {'atualizado_em_original': '2020-01-01T00:00:00Z'}, format='json').status_code, 409)
        response = self.client.delete(url, {'atualizado_em_original': versao}, format='json')
        self.assertEqual(response.status_code, 204, response.data)
        self.compra.refresh_from_db()
        self.assertIsNotNone(self.compra.excluido_em)
        self.assertEqual(self.client.get(self.compras, {'page': 1}).data['count'], 0)
        self.assertEqual(self.client.get(self.compras+'resumo/').data['compras'], 0)
        abastecimento = LancamentoTransporte.objects.get(pk=criada.data['id'])
        self.assertEqual(abastecimento.compra_diesel_id, self.compra.pk)
        self.assertEqual(abastecimento.total, Decimal('712.00'))
        self.assertEqual(self.client.get(self.lancamentos+'preco-silo/', {'data': '2026-10-10', 'tipo_diesel': 'S10'}).status_code, 400)
        self.assertEqual(self.client.patch(url, {'litros': '1', 'atualizado_em_original': versao}, format='json').status_code, 404)
        from apps.core.models import RegistroAlteracao
        self.assertTrue(RegistroAlteracao.objects.filter(modulo='transportes', registro_id=str(self.compra.pk), alteracoes__has_key='excluido em').exists())

    def test_excluir_exige_permissao_propria(self):
        acesso = AcessoUsuario.objects.get(usuario=self.usuario)
        acesso.permissoes = {'transportes': ['consultar', 'editar']}
        acesso.save()
        url = self.compras + str(self.compra.pk) + '/'
        versao = self.client.get(url).data['atualizado_em']
        self.assertEqual(self.client.delete(url, {'atualizado_em_original': versao}, format='json').status_code, 403)
        self.compra.refresh_from_db()
        self.assertIsNone(self.compra.excluido_em)

    def test_preco_ignora_compra_excluida_e_mantem_anterior(self):
        from django.utils import timezone
        CompraDiesel.objects.create(data='2026-10-09', fornecedor='Outro', produtor='NEI', tipo='S10', litros='100', valor_unitario='9', excluido_em=timezone.now())
        resposta = self.client.get(self.lancamentos+'preco-silo/', {'data': '2026-10-10', 'tipo_diesel': 'S10'})
        self.assertEqual(resposta.status_code, 200, resposta.data)
        self.assertEqual(resposta.data['compra'], self.compra.pk)

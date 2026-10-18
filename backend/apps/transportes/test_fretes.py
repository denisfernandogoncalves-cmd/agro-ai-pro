from datetime import date
from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from apps.accounts.models import AcessoUsuario
from apps.graos.test_cargas_colhidas import CargaColhidaBase
from apps.graos.cargas_services import registrar_carga_colhida, cancelar_carga_colhida
from apps.graos.models import CargaColhida
from apps.vendas.test_consulta_romaneios import ContextoVendaMixin
from apps.vendas.services import confirmar_venda, registrar_entrega_venda
from apps.vendas.models import EntregaVendaGraos
from apps.transportes.models import Caminhao, RemuneracaoMotorista, FreteConferido


class FretesCargasTests(CargaColhidaBase, TestCase):
    def setUp(self):
        self.criar_contexto()
        self.client = APIClient()
        self.client.force_authenticate(self.usuario)
        self.carga = registrar_carga_colhida(usuario=self.usuario, **{**self.dados_carga(), "motorista": "Motorista da viagem"})
        self.caminhao = Caminhao.objects.create(placa="ABC1D23", veiculo="Volvo", motorista="Motorista atual")
        self.rem = RemuneracaoMotorista.objects.create(caminhao=self.caminhao, motorista="Motorista da viagem", competencia=date(2026, 8, 1), salario="2000", comissao="50")
        self.url = "/api/transportes/fretes/"
        self.dados = {"carga": self.carga.pk, "entrega": None, "remuneracao": self.rem.pk, "frete": "1000.00", "comissao": "100.00", "ja_contabilizado": False}

    def test_cruza_mes_placa_e_preserva_historico(self):
        resposta = self.client.get(self.url + "cruzamento/", {"mes": "2026-08", "placa": "abc-1d23"})
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(len(resposta.data["viagens"]), 1)
        self.assertEqual(resposta.data["viagens"][0]["motorista"], "Motorista da viagem")
        self.assertEqual(resposta.data["viagens"][0]["placa"], "ABC1D23")
        self.assertIsNone(resposta.data["viagens"][0]["conferencia"])
        self.assertEqual(self.client.get(self.url + "cruzamento/", {"mes": "2026-09"}).data["viagens"], [])
        self.assertEqual(self.client.get(self.url + "cruzamento/", {"mes": "errado"}).status_code, 400)

    def test_base_comissao_peso_produto_sem_tara_antes_dos_descontos(self):
        self.assertLess(self.carga.peso_liquido_kg, self.carga.peso_bruto_kg)
        carga = registrar_carga_colhida(usuario=self.usuario, **{
            **self.dados_carga(), "peso_total_kg": "48000.000", "tara_kg": "20000.000",
            "peso_bruto_kg": "28000.000", "umidade_percentual": "14.00",
            "impureza_percentual": "1.00", "defeitos_percentual": "0.00",
        })
        resposta = self.client.get(self.url + "cruzamento/", {"mes": "2026-08"})
        viagens = {item["id"]: item for item in resposta.data["viagens"]}
        self.assertEqual(Decimal(viagens[carga.pk]["peso_kg"]), Decimal("28000.000"))
        self.assertEqual(Decimal(viagens[self.carga.pk]["peso_kg"]), self.carga.peso_bruto_kg)
        self.assertLess(self.carga.peso_liquido_kg, Decimal(viagens[self.carga.pk]["peso_kg"]))

    def test_comissao_manual_holerite_e_reenvio_sem_duplicar(self):
        resposta = self.client.post(self.url, self.dados, format="json")
        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.assertEqual(str(self.rem.valor_comissao), "150.00")
        holerite = self.client.get("/api/transportes/remuneracoes/imprimir/", {"mes": "2026-08"}).data[0]
        self.assertEqual(holerite["comissao_fretes"], "100.00")
        self.assertEqual(holerite["total"], "2150.00")
        self.assertEqual(self.client.post(self.url, self.dados, format="json").status_code, 400)
        self.assertEqual(FreteConferido.objects.count(), 1)

    def test_ja_contabilizado_e_origem_cancelada_nao_somam(self):
        item = FreteConferido.objects.create(carga=self.carga, remuneracao=self.rem, frete="1000", comissao="100", ja_contabilizado=True)
        self.assertEqual(str(self.rem.valor_comissao), "50.00")
        item.ja_contabilizado = False
        item.save()
        self.assertEqual(str(self.rem.valor_comissao), "150.00")
        cancelar_carga_colhida(usuario=self.usuario, carga=self.carga, motivo="Teste de comissão excluída")
        self.assertEqual(str(self.rem.valor_comissao), "50.00")
        self.assertEqual(self.client.get(self.url + "cruzamento/", {"mes": "2026-08"}).data["viagens"], [])
        self.assertEqual(self.client.post(self.url, self.dados, format="json").status_code, 400)

    def test_validacao_mes_placa_origem_valores_e_decisao(self):
        outro = Caminhao.objects.create(placa="XYZ9A99", veiculo="Outro", motorista="Outro")
        rem_outro = RemuneracaoMotorista.objects.create(caminhao=outro, motorista="Outro", competencia=date(2026, 8, 1))
        for alteracao in ({"carga": None}, {"frete": "-1"}, {"comissao": "-1"}, {"remuneracao": rem_outro.pk}):
            self.assertEqual(self.client.post(self.url, {**self.dados, **alteracao}, format="json").status_code, 400)
        sem_decisao = dict(self.dados)
        del sem_decisao["ja_contabilizado"]
        self.assertEqual(self.client.post(self.url, sem_decisao, format="json").status_code, 400)
        self.rem.competencia = date(2026, 9, 1)
        self.rem.save()
        self.assertEqual(self.client.post(self.url, self.dados, format="json").status_code, 400)

    def test_edicao_obsoleta_e_protecao_da_remuneracao(self):
        item = self.client.post(self.url, self.dados, format="json").data
        url = self.url + str(item["id"]) + "/"
        versao = item["atualizado_em"]
        self.assertEqual(self.client.patch(url, {"comissao": "200", "atualizado_em_original": versao}, format="json").status_code, 200)
        self.assertEqual(self.client.patch(url, {"comissao": "300", "atualizado_em_original": versao}, format="json").status_code, 409)
        self.assertEqual(str(self.rem.valor_comissao), "250.00")
        self.assertEqual(self.client.delete(f"/api/transportes/remuneracoes/{self.rem.pk}/").status_code, 400)
        self.assertEqual(self.client.patch(f"/api/transportes/remuneracoes/{self.rem.pk}/", {"competencia": "2026-09-01", "comissao_percentual": "0"}, format="json").status_code, 400)
        self.assertEqual(self.client.delete(url).status_code, 405)

    def test_acesso_a_origem_e_acao(self):
        AcessoUsuario.objects.create(usuario=self.usuario, modulos=["transportes"], permissoes={"transportes": ["consultar", "cadastrar"]})
        self.assertEqual(self.client.get(self.url + "cruzamento/", {"mes": "2026-08"}).data["viagens"], [])
        self.assertEqual(self.client.post(self.url, self.dados, format="json").status_code, 403)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(self.url + "cruzamento/", {"mes": "2026-08"}).status_code, 401)


class FretesVendasTests(ContextoVendaMixin, TestCase):
    def test_cruza_entrega_e_comissao_sem_usar_valor_do_grao(self):
        self.criar_contexto(saldo="10000")
        venda = self.rascunho(quantidade="1000")
        confirmar_venda(usuario=self.usuario, venda=venda, chave_idempotencia="confirmar-frete")
        entrega = registrar_entrega_venda(usuario=self.usuario, venda=venda, quantidade_kg="100", peso_bruto_kg="1100", tara_kg="1000", chave_idempotencia="entrega-frete", data_entrega=date(2026, 8, 10), placa="ABC1D23", motorista="Motorista")
        caminhao = Caminhao.objects.create(placa="ABC1D23", veiculo="Volvo", motorista="Atual")
        rem = RemuneracaoMotorista.objects.create(caminhao=caminhao, motorista="Motorista", competencia=date(2026, 8, 1), salario="1000", comissao="0")
        client = APIClient()
        client.force_authenticate(self.usuario)
        viagens = client.get("/api/transportes/fretes/cruzamento/", {"mes": "2026-08"}).data["viagens"]
        self.assertEqual(viagens[0]["origem"], "venda")
        self.assertEqual(viagens[0]["id"], entrega.pk)
        self.assertEqual(Decimal(viagens[0]["peso_kg"]), Decimal("100"))
        resposta = client.post("/api/transportes/fretes/", {"entrega": entrega.pk, "remuneracao": rem.pk, "frete": "400", "comissao": "40", "ja_contabilizado": False}, format="json")
        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.assertEqual(str(rem.valor_comissao), "40.00")
        EntregaVendaGraos.objects.filter(pk=entrega.pk).update(cancelado_em=entrega.criado_em)
        self.assertEqual(str(rem.valor_comissao), "0.00")

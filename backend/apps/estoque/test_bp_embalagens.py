import uuid

from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

from apps.financeiro.models import ParceiroFinanceiro
from apps.propriedades.models import Propriedade
from .models import ProdutoEstoque


class BPEmbalagensTests(APITestCase):
    def setUp(self):
        self.client.force_authenticate(get_user_model().objects.create_user("bp-teste"))
        self.propriedade = Propriedade.objects.create(nome="Teste BP", municipio="Teste", area_hectares="24.20", bp_cvale="00100371854")
        self.cvale = ParceiroFinanceiro.objects.create(nome="C.Vale", tipo="fornecedor")
        self.outra = ParceiroFinanceiro.objects.create(nome="Outra empresa", tipo="fornecedor")
        self.produto = ProdutoEstoque.objects.create(nome="Insumo", categoria="insumo", unidade="l")
        self.dados = {
            "id": str(uuid.uuid4()), "fornecedor": self.cvale.pk, "produto": self.produto.pk,
            "data_envio": "2026-10-01", "embalagem": "Balde", "conteudo_embalagem": "20",
            "dosagem_alqueire": "2.5",
            "itens": [{"propriedade": self.propriedade.pk, "cad_pro": "", "area_alqueires": "10"}],
        }

    def previa(self):
        return self.client.post("/api/estoque/faturamentos/previa/", self.dados, format="json")

    def test_arredonda_embalagens_para_cima_e_converte_conteudo(self):
        resposta = self.previa()
        self.assertEqual(resposta.status_code, 200, resposta.data)
        item = resposta.data["itens"][0]
        self.assertEqual(item["quantidade_sugerida"], "25.000")
        self.assertEqual(item["quantidade_embalagens"], "2")
        self.assertEqual(item["quantidade"], "40.000")

    def test_quantidade_manual_prevalece_sobre_sugestao(self):
        self.dados["itens"][0]["quantidade_embalagens"] = "7"
        resposta = self.previa()
        self.assertEqual(resposta.status_code, 200, resposta.data)
        self.assertEqual(resposta.data["itens"][0]["quantidade_embalagens"], "7.000")

    def test_embalagens_exatas_nao_recebem_uma_extra(self):
        self.dados["dosagem_alqueire"] = "4"
        self.assertEqual(self.previa().data["itens"][0]["quantidade_embalagens"], "2")

    def test_bp_automatico_apenas_cvale_e_pode_ser_ajustado_no_envio(self):
        self.assertEqual(self.previa().data["itens"][0]["bep"], "00100371854")
        self.dados["itens"][0]["bep"] = "000123"
        self.assertEqual(self.previa().data["itens"][0]["bep"], "000123")
        self.dados["fornecedor"] = self.outra.pk
        self.assertEqual(self.previa().status_code, 400)
        self.dados["itens"][0].pop("bep")
        resposta = self.previa()
        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(resposta.data["usa_bep"])
        self.assertEqual(resposta.data["itens"][0]["bep"], "")

    def test_bp_cadastrado_preserva_zeros_e_edicao_e_opcional(self):
        url = f"/api/propriedades/{self.propriedade.pk}/"
        resposta = self.client.patch(url, {"bp_cvale": "000789"}, format="json")
        self.assertEqual(resposta.status_code, 200, resposta.data)
        self.assertEqual(self.client.get(url).data["bp_cvale"], "000789")
        self.assertEqual(self.client.patch(url, {"bp_cvale": "ABC"}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(url, {"bp_cvale": ""}, format="json").status_code, 200)

    def test_alterar_bp_nao_altera_snapshot_de_envio_anterior(self):
        resposta = self.client.post("/api/estoque/faturamentos/confirmar/", self.dados, format="json")
        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.propriedade.bp_cvale = "999"
        self.propriedade.save(update_fields=("bp_cvale",))
        salvo = self.client.get(f"/api/estoque/faturamentos/{resposta.data['id']}/").data
        self.assertEqual(salvo["resumo"]["itens"][0]["bep"], "00100371854")
        repetido = self.client.post("/api/estoque/faturamentos/confirmar/", self.dados, format="json")
        self.assertEqual(repetido.status_code, 200)
        self.assertEqual(repetido.data["resumo"], salvo["resumo"])

    def test_zero_sem_override_exige_quantidade_valida(self):
        self.dados["dosagem_alqueire"] = "0"
        self.assertEqual(self.previa().status_code, 400)

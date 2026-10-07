import uuid
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db.models.deletion import ProtectedError
from django.db import close_old_connections, connection
from django.test import TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from apps.cadpro.models import CADPro, CADProPropriedade
from apps.financeiro.models import ParceiroFinanceiro
from apps.propriedades.models import Propriedade
from .models import BaixaFaturamentoInsumo, FaturamentoInsumo, LoteEstoque, MovimentacaoEstoque, ProdutoEstoque
from .services import registrar_movimentacao, saldo_lote
from .faturamento import FaturamentoEntrada, assinatura, fornecedor_usa_bep


class FaturamentoInsumosTests(APITestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user("faturamento-teste")
        self.client.force_authenticate(self.usuario)
        self.empresa = ParceiroFinanceiro.objects.create(nome="Empresa A", tipo="fornecedor")
        self.outra = ParceiroFinanceiro.objects.create(nome="Empresa B", tipo="fornecedor")
        self.produto = ProdutoEstoque.objects.create(nome="Produto teste", categoria="insumo", unidade="l")
        self.propriedade = Propriedade.objects.create(nome="Fazenda teste", proprietario="Produtor teste", municipio="Teste", area_hectares="24.20")
        self.cad = CADPro.objects.create(codigo="123", descricao="Cadastro teste")
        CADProPropriedade.objects.create(cad_pro=self.cad, propriedade=self.propriedade)
        self.lote = self.entrada(self.empresa, "60")
        self.outro_lote = self.entrada(self.outra, "200")
        self.dados = {
            "id": str(uuid.uuid4()), "fornecedor": self.empresa.pk, "produto": self.produto.pk,
            "data_envio": str(timezone.localdate()), "embalagem": "Balde", "conteudo_embalagem": "20",
            "dosagem_alqueire": "2.5", "observacoes": "Teste sintético",
            "itens": [{"propriedade": self.propriedade.pk, "cad_pro": "123", "area_alqueires": "10", "quantidade_embalagens": "4"}],
        }

    def entrada(self, empresa, quantidade):
        lote = LoteEstoque.objects.create(produto=self.produto, fornecedor=empresa, codigo=str(uuid.uuid4()))
        registrar_movimentacao(usuario=self.usuario, lote=lote, tipo="entrada", quantidade=quantidade, custo_unitario="1")
        return lote

    def post(self, action="confirmar", dados=None):
        return self.client.post(f"/api/estoque/faturamentos/{action}/", dados or self.dados, format="json")

    def test_previa_nao_movimenta_e_calcula_dosagem(self):
        resposta = self.post("previa")
        self.assertEqual(resposta.status_code, 200, resposta.data)
        self.assertEqual(Decimal(resposta.data["saldo_posterior"]), -20)
        self.assertEqual(Decimal(resposta.data["itens"][0]["quantidade_sugerida"]), 25)
        self.assertEqual(saldo_lote(self.lote), 60)
        self.assertFalse(FaturamentoInsumo.objects.exists())

    def test_confirmacao_negativa_isola_empresa_e_aparece_na_disponibilidade(self):
        resposta = self.post()
        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.assertEqual(Decimal(resposta.data["resumo"]["quantidade_total"]), 80)
        self.assertEqual(saldo_lote(self.outro_lote), 200)
        self.assertEqual(sum(saldo_lote(l) for l in LoteEstoque.objects.filter(fornecedor=self.empresa)), -20)
        consulta = self.client.get("/api/estoque/disponibilidade/", {"fornecedor": self.empresa.pk, "somente_disponivel": "false"})
        self.assertEqual(consulta.status_code, 200, consulta.data)
        self.assertEqual(Decimal(consulta.data["resumo"][0]["disponivel"]), -20)
        self.assertIsNone(consulta.data["resumo"][0]["preco_medio"])

    def test_repeticao_nao_duplica_e_alteracao_conflita(self):
        self.assertEqual(self.post().status_code, 201)
        self.assertEqual(self.post().status_code, 200)
        self.assertEqual(FaturamentoInsumo.objects.count(), 1)
        self.assertEqual(BaixaFaturamentoInsumo.objects.count(), 2)
        self.dados["itens"][0]["quantidade_embalagens"] = "5"
        self.assertEqual(self.post().status_code, 409)

    def test_sem_entrada_permite_negativo(self):
        terceira = ParceiroFinanceiro.objects.create(nome="Empresa C", tipo="fornecedor")
        self.dados["fornecedor"] = terceira.pk
        resposta = self.post()
        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.assertEqual(saldo_lote(LoteEstoque.objects.get(fornecedor=terceira)), -80)

    def test_saida_comum_continua_bloqueada_e_nao_aceita_override(self):
        resposta = self.client.post("/api/estoque/movimentacoes/", {"lote": self.lote.pk, "tipo": "saida", "quantidade": "80", "permitir_negativo": True}, format="json")
        self.assertEqual(resposta.status_code, 400)
        self.assertEqual(saldo_lote(self.lote), 60)

    def test_quantidades_cadpro_e_duplicidade_validados(self):
        for campo, valor in [("quantidade_embalagens", "0"), ("quantidade_embalagens", "-1"), ("cad_pro", "999"), ("area_alqueires", "0")]:
            dados = {**self.dados, "itens": [{**self.dados["itens"][0], campo: valor}]}
            self.assertEqual(self.post(dados=dados).status_code, 400)
        self.assertEqual(self.post(dados={**self.dados, "itens": self.dados["itens"] * 2}).status_code, 400)
        self.assertFalse(FaturamentoInsumo.objects.exists())

    def test_rollback_integral_se_baixa_falhar(self):
        with patch("apps.estoque.faturamento.BaixaFaturamentoInsumo.objects.create", side_effect=RuntimeError("falha simulada")):
            with self.assertRaises(RuntimeError):
                self.post()
        self.assertEqual(saldo_lote(self.lote), 60)
        self.assertFalse(FaturamentoInsumo.objects.exists())
        self.assertEqual(MovimentacaoEstoque.objects.count(), 2)

    def test_historico_preserva_nomes_e_baixas_nao_podem_ser_excluidas(self):
        salvo = self.post().data
        self.propriedade.nome = "Nome alterado"
        self.propriedade.save()
        detalhe = self.client.get(f"/api/estoque/faturamentos/{salvo['id']}/")
        self.assertEqual(detalhe.data["resumo"]["itens"][0]["propriedade_nome"], "Fazenda teste")
        baixa = BaixaFaturamentoInsumo.objects.first()
        self.assertEqual(self.client.delete(f"/api/estoque/movimentacoes/{baixa.movimento_id}/").status_code, 409)
        with self.assertRaises(ProtectedError):
            baixa.movimento.delete()

    def test_bep_cvale_snapshot_e_zeros_a_esquerda(self):
        self.empresa.nome = "C.VALE - Cooperativa Agroindustrial"
        self.empresa.save()
        self.dados["itens"][0]["bep"] = "00100371854"
        previa = self.post("previa")
        self.assertTrue(previa.data["usa_bep"])
        self.assertEqual(previa.data["itens"][0]["bep"], "00100371854")
        salvo = self.post().data
        self.empresa.nome = "Nome alterado"
        self.empresa.save()
        detalhe = self.client.get(f"/api/estoque/faturamentos/{salvo['id']}/")
        self.assertTrue(detalhe.data["resumo"]["usa_bep"])
        self.assertEqual(detalhe.data["resumo"]["itens"][0]["cad_pro"], "123")
        self.assertEqual(detalhe.data["resumo"]["itens"][0]["bep"], "00100371854")

    def test_bep_opcional_por_propriedade_e_repetido(self):
        self.empresa.nome = "C Vale"
        self.empresa.save()
        outra = Propriedade.objects.create(nome="Outra área", municipio="Teste", area_hectares="2.42")
        self.dados["itens"].append({"propriedade": outra.pk, "area_alqueires": "1", "quantidade_embalagens": "1"})
        self.assertEqual(self.post("previa").status_code, 200)
        for item in self.dados["itens"]:
            item["bep"] = "100183369"
        self.assertEqual(self.post().status_code, 201)
        self.assertEqual(len(FaturamentoInsumo.objects.get().resumo["itens"]), 2)

    def test_bep_valida_empresa_e_digitos(self):
        self.dados["itens"][0]["bep"] = "123"
        self.assertEqual(self.post("previa").status_code, 400)
        self.empresa.nome = "C.Vale"
        self.empresa.save()
        for valor in ("ABC", "12.34", "1" * 41):
            self.dados["itens"][0]["bep"] = valor
            self.assertEqual(self.post("previa").status_code, 400)
        self.assertFalse(FaturamentoInsumo.objects.exists())
        for nome in ("C.Vale", "CVALE", " c vale ", "C-VALE Cooperativa"):
            self.assertTrue(fornecedor_usa_bep(nome))
        for nome in ("Outra empresa", "C Valerio", "Fornecedor C.Vale"):
            self.assertFalse(fornecedor_usa_bep(nome))

    def test_bep_vazio_preserva_assinatura_anterior(self):
        entrada = FaturamentoEntrada(data=self.dados)
        entrada.is_valid(raise_exception=True)
        antigo = dict(entrada.validated_data)
        antigo["itens"] = [{k: v for k, v in item.items() if k != "bep"} for item in antigo["itens"]]
        hash_antigo = hashlib.sha256(json.dumps(antigo, default=lambda v: str(v.pk) if hasattr(v, "pk") else str(v), sort_keys=True).encode()).hexdigest()
        self.assertEqual(assinatura(entrada.validated_data), hash_antigo)

    def test_excluir_recompoe_lotes_e_preserva_auditoria(self):
        salvo = self.post().data
        url = f"/api/estoque/faturamentos/{salvo['id']}/"
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertEqual(saldo_lote(self.lote), 60)
        self.assertEqual(saldo_lote(self.outro_lote), 200)
        self.assertEqual(sum(saldo_lote(l) for l in LoteEstoque.objects.filter(fornecedor=self.empresa)), 60)
        self.assertEqual(MovimentacaoEstoque.objects.count(), 2)
        faturamento = FaturamentoInsumo.objects.get(pk=salvo["id"])
        self.assertEqual(faturamento.excluido_por, self.usuario)
        self.assertIsNotNone(faturamento.excluido_em)
        self.assertEqual(len(faturamento.resumo["baixas_excluidas"]), 2)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.get(url + "pdf/").status_code, 404)
        self.assertEqual(self.client.get("/api/estoque/faturamentos/").data, [])
        self.assertEqual(self.post().status_code, 409)

    def test_exclusao_nao_reverte_outro_faturamento(self):
        primeiro = self.post().data
        self.dados["id"] = str(uuid.uuid4())
        segundo = self.post().data
        self.client.delete(f"/api/estoque/faturamentos/{primeiro['id']}/")
        self.assertEqual(sum(saldo_lote(l) for l in LoteEstoque.objects.filter(fornecedor=self.empresa)), -20)
        self.assertEqual(self.client.get(f"/api/estoque/faturamentos/{segundo['id']}/").status_code, 200)

    def test_exclusao_falha_reverte_todas_as_alteracoes(self):
        salvo = self.post().data
        with patch("apps.estoque.faturamento.timezone.now", side_effect=RuntimeError("falha simulada")):
            with self.assertRaises(RuntimeError):
                self.client.delete(f"/api/estoque/faturamentos/{salvo['id']}/")
        self.assertIsNone(FaturamentoInsumo.objects.get().excluido_em)
        self.assertEqual(BaixaFaturamentoInsumo.objects.count(), 2)
        self.assertEqual(sum(saldo_lote(l) for l in LoteEstoque.objects.filter(fornecedor=self.empresa)), -20)

    def test_pdf_individual_e_compatibilidade_com_snapshot_antigo(self):
        salvo = self.post().data
        url = f"/api/estoque/faturamentos/{salvo['id']}/pdf/"
        resposta = self.client.get(url)
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta["Content-Type"], "application/pdf")
        self.assertIn(salvo["id"], resposta["Content-Disposition"])
        self.assertEqual(resposta["Cache-Control"], "private, no-store")
        self.assertTrue(resposta.content.startswith(b"%PDF-"))
        self.assertTrue(resposta.content.rstrip().endswith(b"%%EOF"))
        faturamento = FaturamentoInsumo.objects.get()
        faturamento.resumo.pop("usa_bep")
        faturamento.resumo["itens"][0].pop("bep")
        faturamento.save()
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_exclusao_e_pdf_exigem_autenticacao_e_id_valido(self):
        salvo = self.post().data
        url = f"/api/estoque/faturamentos/{salvo['id']}/"
        self.assertEqual(self.client.delete("/api/estoque/faturamentos/invalido/").status_code, 404)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.delete(url).status_code, 401)
        self.assertEqual(self.client.get(url + "pdf/").status_code, 401)
        self.assertIsNone(FaturamentoInsumo.objects.get().excluido_em)

    def test_exige_autenticacao(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.post().status_code, 401)
        self.assertEqual(self.post("previa").status_code, 401)
        self.assertEqual(self.client.get("/api/estoque/faturamentos/").status_code, 401)

    def test_entrada_posterior_compensa_saldo_global(self):
        self.post()
        self.entrada(self.empresa, "100")
        consulta = self.client.get("/api/estoque/disponibilidade/", {"fornecedor": self.empresa.pk, "somente_disponivel": "true"})
        self.assertEqual(Decimal(consulta.data["resumo"][0]["disponivel"]), 80)

    def test_protege_unidade_e_empresa_do_lote(self):
        self.post()
        self.assertEqual(self.client.patch(f"/api/estoque/produtos/{self.produto.pk}/", {"unidade": "kg"}).status_code, 400)
        self.assertEqual(self.client.patch(f"/api/estoque/lotes/{self.lote.pk}/", {"fornecedor": self.outra.pk}).status_code, 400)


@skipUnless(connection.vendor == "postgresql", "Bloqueios concorrentes exigem PostgreSQL")
class FaturamentoConcorrenciaTests(TransactionTestCase):
    def test_exclusoes_concorrentes_devolvem_uma_vez(self):
        usuario = get_user_model().objects.create_user("exclusao-concorrente")
        empresa = ParceiroFinanceiro.objects.create(nome="C.Vale", tipo="fornecedor")
        produto = ProdutoEstoque.objects.create(nome="Insumo", categoria="insumo", unidade="l")
        propriedade = Propriedade.objects.create(nome="Propriedade", municipio="Teste", area_hectares="2.42")
        client = APIClient()
        client.force_authenticate(usuario)
        dados = {"id": str(uuid.uuid4()), "fornecedor": empresa.pk, "produto": produto.pk,
                 "data_envio": str(timezone.localdate()), "embalagem": "Balde", "conteudo_embalagem": "20",
                 "dosagem_alqueire": "0", "itens": [{"propriedade": propriedade.pk, "bep": "00123", "area_alqueires": "1", "quantidade_embalagens": "4"}]}
        self.assertEqual(client.post("/api/estoque/faturamentos/confirmar/", dados, format="json").status_code, 201)
        barreira = Barrier(2)
        def excluir(_):
            close_old_connections()
            try:
                cliente = APIClient()
                cliente.force_authenticate(get_user_model().objects.get(pk=usuario.pk))
                barreira.wait(timeout=10)
                return cliente.delete(f"/api/estoque/faturamentos/{dados['id']}/").status_code
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(list(pool.map(excluir, range(2))), [204, 204])
        self.assertEqual(saldo_lote(LoteEstoque.objects.get(produto=produto)), 0)
        self.assertEqual(len(FaturamentoInsumo.objects.get().resumo["baixas_excluidas"]), 1)

    def test_mesma_confirmacao_concorrente_baixa_uma_vez(self):
        usuario = get_user_model().objects.create_user("concorrencia-faturamento")
        empresa = ParceiroFinanceiro.objects.create(nome="Empresa concorrência", tipo="fornecedor")
        produto = ProdutoEstoque.objects.create(nome="Insumo concorrência", categoria="insumo", unidade="l")
        propriedade = Propriedade.objects.create(nome="Propriedade concorrência", municipio="Teste", area_hectares="2.42")
        dados = {"id": str(uuid.uuid4()), "fornecedor": empresa.pk, "produto": produto.pk,
                 "data_envio": str(timezone.localdate()), "embalagem": "Balde", "conteudo_embalagem": "20",
                 "dosagem_alqueire": "0", "itens": [{"propriedade": propriedade.pk, "area_alqueires": "1", "quantidade_embalagens": "4"}]}
        barreira = Barrier(2)
        def enviar(_):
            close_old_connections()
            try:
                client = APIClient()
                client.force_authenticate(get_user_model().objects.get(pk=usuario.pk))
                barreira.wait(timeout=10)
                return client.post("/api/estoque/faturamentos/confirmar/", dados, format="json").status_code
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            respostas = list(pool.map(enviar, range(2)))
        self.assertCountEqual(respostas, [200, 201])
        self.assertEqual(FaturamentoInsumo.objects.count(), 1)
        self.assertEqual(MovimentacaoEstoque.objects.count(), 1)
        self.assertEqual(saldo_lote(LoteEstoque.objects.get(produto=produto)), -80)

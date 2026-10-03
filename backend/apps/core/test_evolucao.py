from decimal import Decimal
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken
from apps.accounts.access import ACOES
from apps.accounts.models import AcessoUsuario
from apps.propriedades.models import Propriedade
from apps.financeiro.models import LancamentoFinanceiro
from apps.estoque.models import ProdutoEstoque
from .models import FavoritoFiltro, RegistroAlteracao
from .auditoria import requisicao_atual
from .painel import construir_painel


class EvolucaoTests(APITestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user("gestor-painel", is_staff=True)
        self.user = get_user_model().objects.create_user("consulta-painel")
        self.acesso = AcessoUsuario.objects.create(usuario=self.user, modulos=["financeiro", "propriedades"], permissoes={"financeiro": ["consultar"], "propriedades": ["consultar"]})
        self.propriedade = Propriedade.objects.create(nome="Fazenda", municipio="Cidade", uf="PR", area_hectares="24.20", proprietario="")
        self.login(self.user)

    def login(self, user):
        self.client.force_authenticate(user=None)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(user)}")

    def test_consultar_nao_permite_cadastrar_editar_ou_excluir(self):
        self.assertEqual(self.client.get("/api/propriedades/").status_code, 200)
        for method, url, data in [("post", "/api/propriedades/", {"nome": "Outra"}), ("patch", f"/api/propriedades/{self.propriedade.pk}/", {"nome": "Mudou"}), ("delete", f"/api/propriedades/{self.propriedade.pk}/", {})]:
            with self.subTest(method=method):
                self.assertEqual(getattr(self.client, method)(url, data, format="json").status_code, 403)
        self.propriedade.refresh_from_db()
        self.assertEqual(self.propriedade.nome, "Fazenda")

    def test_permissao_editar_nao_concede_excluir(self):
        self.acesso.permissoes = {"propriedades": ["consultar", "editar"]}
        self.acesso.save()
        self.assertEqual(self.client.patch(f"/api/propriedades/{self.propriedade.pk}/", {"nome": "Editada"}, format="json").status_code, 200)
        self.assertEqual(self.client.delete(f"/api/propriedades/{self.propriedade.pk}/").status_code, 403)

    def test_legado_conserva_acoes_e_administrador_nao_perde_acesso(self):
        self.acesso.permissoes = None
        self.acesso.save()
        resposta = self.client.get("/api/auth/me/")
        self.assertEqual(set(resposta.data["permissoes"]["propriedades"]), set(ACOES))
        self.login(self.admin)
        self.assertEqual(self.client.get("/api/core/historico/").status_code, 200)

    def test_validacao_permissoes_impede_modulos_desconhecidos_e_acao_sem_consulta(self):
        self.login(self.admin)
        for valor in [{"financeiro": ["editar"]}, {"desconhecido": ["consultar"]}, {"financeiro": ["aprovar"]}]:
            self.assertEqual(self.client.patch(f"/api/auth/users/{self.user.pk}/", {"permissoes": valor}, format="json").status_code, 400)
        self.acesso.refresh_from_db()
        self.assertEqual(self.acesso.permissoes["financeiro"], ["consultar"])

    def test_painel_restringe_dados_ao_setor_permitido(self):
        ProdutoEstoque.objects.create(nome="Restrito", categoria="insumo", unidade="kg", estoque_minimo="10")
        resultado = self.client.get("/api/core/painel/")
        self.assertEqual(resultado.status_code, 200, resultado.data)
        self.assertNotIn("estoque_baixo", resultado.data["resumo"])
        self.assertTrue(all(item["modulo"] != "estoque" for item in resultado.data["alertas"]))
        self.assertTrue(any(item["tipo"] == "cadastro-incompleto" for item in resultado.data["alertas"]))

    def test_painel_financeiro_vencimentos_duplicatas_e_filtros(self):
        dados = dict(tipo="pagar", descricao="Conta repetida", valor=Decimal("100"), data_vencimento=timezone.localdate()-timedelta(days=1), propriedade=self.propriedade, safra="2026")
        LancamentoFinanceiro.objects.create(**dados)
        LancamentoFinanceiro.objects.create(**dados)
        resposta = self.client.get("/api/core/painel/", {"propriedade": self.propriedade.pk, "safra": "2026"})
        self.assertEqual(Decimal(resposta.data["resumo"]["a_pagar"]), Decimal("200"))
        tipos = {item["tipo"] for item in resposta.data["alertas"]}
        self.assertIn("conta-vencida", tipos)
        self.assertIn("possivel-duplicata-financeiro", tipos)
        self.assertEqual(LancamentoFinanceiro.objects.count(), 2)
        sem_dados = self.client.get("/api/core/painel/", {"safra": "2027"})
        self.assertEqual(Decimal(sem_dados.data["resumo"]["a_pagar"]), Decimal("0"))

    def test_painel_usuario_sem_modulos_nao_vaza_totais(self):
        self.acesso.modulos = []
        self.acesso.save()
        resposta = self.client.get("/api/core/painel/")
        self.assertEqual(resposta.data["resumo"], {})
        self.assertEqual(resposta.data["alertas"], [])

    def test_painel_parametros_invalidos(self):
        self.assertEqual(self.client.get("/api/core/painel/", {"propriedade": "inválida"}).status_code, 400)
        self.assertEqual(self.client.get("/api/core/painel/", {"safra": "a"*21}).status_code, 400)

    def test_favoritos_persistem_sao_privados_e_validam_contexto(self):
        dados = {"contexto": "financeiro", "nome": "Safra", "filtros": {"search": "Soja", "status": "pendente"}}
        resposta = self.client.post("/api/core/favoritos/", dados, format="json")
        self.assertEqual(resposta.status_code, 201, resposta.data)
        pk = resposta.data["id"]
        self.assertEqual(self.client.get("/api/core/favoritos/", {"contexto": "financeiro"}).data[0]["filtros"]["search"], "Soja")
        self.login(self.admin)
        self.assertEqual(self.client.get("/api/core/favoritos/").data, [])
        self.assertEqual(self.client.delete(f"/api/core/favoritos/{pk}/").status_code, 404)
        self.login(self.user)
        self.assertEqual(self.client.post("/api/core/favoritos/", {**dados, "contexto": "vendas"}, format="json").status_code, 400)
        self.assertEqual(self.client.post("/api/core/favoritos/", {**dados, "filtros": {"password": "não salvar"}}, format="json").status_code, 400)
        self.assertEqual(self.client.post("/api/core/favoritos/", dados, format="json").status_code, 400)
        self.assertEqual(self.client.delete(f"/api/core/favoritos/{pk}/").status_code, 204)

    def test_historico_registra_ator_campos_e_nao_expoe_senha(self):
        self.login(self.admin)
        resposta = self.client.patch(f"/api/propriedades/{self.propriedade.pk}/", {"nome": "Nova fazenda"}, format="json")
        self.assertEqual(resposta.status_code, 200)
        registro = RegistroAlteracao.objects.filter(modulo="propriedades", registro_id=str(self.propriedade.pk)).get()
        self.assertEqual(registro.usuario, self.admin)
        self.assertEqual(registro.alteracoes["nome"], {"antes": "Fazenda", "depois": "Nova fazenda"})
        self.client.patch(f"/api/auth/users/{self.user.pk}/", {"first_name": "Ana"}, format="json")
        user_log = RegistroAlteracao.objects.filter(modulo="usuarios").latest("id")
        self.assertNotIn("password", str(user_log.alteracoes))
        self.assertNotIn(self.user.password, str(user_log.alteracoes))
        self.login(self.user)
        self.assertEqual(self.client.get("/api/core/historico/").status_code, 403)

    def test_historico_imutavel_e_transacao_revertida_nao_registra(self):
        from types import SimpleNamespace
        token = requisicao_atual.set(SimpleNamespace(user=self.admin))
        try:
            try:
                with transaction.atomic():
                    self.propriedade.nome = "Reverter"
                    self.propriedade.save()
                    raise RuntimeError("teste de rollback")
            except RuntimeError:
                pass
            self.assertFalse(RegistroAlteracao.objects.exists())
            self.propriedade.refresh_from_db()
            self.propriedade.nome = "Salvar"
            self.propriedade.save()
            registro = RegistroAlteracao.objects.get()
            with self.assertRaises(ValidationError):
                registro.delete()
            with self.assertRaises(ValidationError):
                RegistroAlteracao.objects.update(acao="excluir")
        finally:
            requisicao_atual.reset(token)

    def test_anonimo_nao_acessa_novos_endpoints(self):
        self.client.credentials()
        for url in ["/api/core/painel/", "/api/core/favoritos/", "/api/core/historico/"]:
            self.assertEqual(self.client.get(url).status_code, 401)

    def test_permissoes_acoes_compostas_pdf_e_confirmacao(self):
        from apps.accounts.access import acao_da_requisicao
        for path, method, esperado in [
            ("/api/estoque/faturamentos/confirmar/", "POST", "cadastrar"),
            ("/api/estoque/faturamentos/previa/", "POST", "consultar"),
            ("/api/estoque/faturamentos/uuid/pdf/", "GET", "imprimir"),
            ("/api/graos/saldos/confirmar-entrega/", "POST", "editar"),
            ("/api/graos/saldos/estornar-movimentacao/", "POST", "excluir"),
        ]:
            with self.subTest(path=path):
                self.assertEqual(acao_da_requisicao(path, method), esperado)
        self.acesso.modulos = ["faturamento-insumos"]
        self.acesso.permissoes = {"faturamento-insumos": ["consultar"]}
        self.acesso.save()
        self.assertEqual(self.client.get("/api/estoque/faturamentos/00000000-0000-0000-0000-000000000001/pdf/").status_code, 403)
        self.assertEqual(self.client.post("/api/estoque/faturamentos/confirmar/", {}, format="json").status_code, 403)
        self.assertEqual(self.client.post("/api/estoque/faturamentos/previa/", {}, format="json").status_code, 400)

    def test_estoque_minimo_soma_lotes_e_limita_avisos(self):
        from apps.estoque.models import LoteEstoque, MovimentacaoEstoque
        produto = ProdutoEstoque.objects.create(nome="Produto", categoria="insumo", unidade="kg", estoque_minimo="10")
        for numero in range(2):
            lote = LoteEstoque.objects.create(produto=produto, codigo=f"lote-{numero}")
            MovimentacaoEstoque.objects.create(lote=lote, tipo="entrada", quantidade="6", custo_unitario="1", criado_por=self.admin, data_movimento=timezone.localdate())
        self.assertEqual(construir_painel(self.admin)["resumo"]["estoque_baixo"], 0)
        ProdutoEstoque.objects.bulk_create([ProdutoEstoque(nome=f"Sem estoque {n}", categoria="insumo", unidade="kg", estoque_minimo="1") for n in range(55)])
        painel = construir_painel(self.admin)
        self.assertEqual(painel["resumo"]["estoque_baixo"], 55)
        self.assertEqual(sum(item["tipo"] == "estoque-baixo" for item in painel["alertas"]), 50)

    def test_historico_registra_apenas_campos_realmente_persistidos(self):
        from types import SimpleNamespace
        token = requisicao_atual.set(SimpleNamespace(user=self.admin, path="/api/propriedades/"))
        try:
            self.propriedade.nome = "Persistido"
            self.propriedade.municipio = "Alteracao nao salva"
            self.propriedade.save(update_fields=["nome"])
            registro = RegistroAlteracao.objects.get()
            self.assertEqual(set(registro.alteracoes), {"nome"})
            self.assertEqual(registro.alteracoes["nome"]["depois"], "Persistido")
        finally:
            requisicao_atual.reset(token)

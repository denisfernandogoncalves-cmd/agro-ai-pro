from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.clima.models import PrevisaoClima
from apps.estoque.models import LocalEstoque, LoteEstoque, ProdutoEstoque
from apps.financeiro.models import CategoriaFinanceira, LancamentoFinanceiro
from apps.maquinas.models import Maquina
from apps.producao.models import OperacaoAgricola
from apps.talhoes.models import Talhao

from .models import AcessoPropriedade, Propriedade


@override_settings(PROPERTY_ACCESS_LEGACY_TEST_MODE=False)
class ControleMultiusuarioApiTests(APITestCase):
    def setUp(self):
        Usuario = get_user_model()
        self.admin = Usuario.objects.create_user("admin_prop", password="x")
        self.gestor = Usuario.objects.create_user("gestor_prop", password="x")
        self.operador = Usuario.objects.create_user("operador_prop", password="x")
        self.leitura = Usuario.objects.create_user("leitura_prop", password="x")
        self.outro = Usuario.objects.create_user("sem_acesso", password="x")
        self.superusuario = Usuario.objects.create_superuser(
            "super_prop",
            "super@example.com",
            "x",
        )
        self.propriedade_a = Propriedade.objects.create(
            nome="Fazenda A",
            municipio="Ivaiporã",
            uf="PR",
            area_hectares="100",
        )
        self.propriedade_b = Propriedade.objects.create(
            nome="Fazenda B",
            municipio="Arapuã",
            uf="PR",
            area_hectares="120",
        )
        for usuario, papel in (
            (self.admin, AcessoPropriedade.Papel.ADMINISTRADOR),
            (self.gestor, AcessoPropriedade.Papel.GESTOR),
            (self.operador, AcessoPropriedade.Papel.OPERADOR),
            (self.leitura, AcessoPropriedade.Papel.LEITURA),
        ):
            AcessoPropriedade.objects.create(
                propriedade=self.propriedade_a,
                usuario=usuario,
                papel=papel,
            )

        self.talhao_a = Talhao.objects.create(
            propriedade=self.propriedade_a,
            nome="Talhão A",
            area_hectares="40",
            safra="2026/2027",
        )
        self.talhao_b = Talhao.objects.create(
            propriedade=self.propriedade_b,
            nome="Talhão B",
            area_hectares="50",
            safra="2026/2027",
        )
        categoria = CategoriaFinanceira.objects.create(
            nome="Custeio",
            aplicacao=CategoriaFinanceira.Aplicacao.DESPESA,
        )
        self.financeiro_a = LancamentoFinanceiro.objects.create(
            tipo=LancamentoFinanceiro.Tipo.PAGAR,
            descricao="Conta A",
            valor="100",
            categoria=categoria,
            propriedade=self.propriedade_a,
            safra="2026/2027",
            data_vencimento=timezone.localdate() + timedelta(days=10),
        )
        self.financeiro_b = LancamentoFinanceiro.objects.create(
            tipo=LancamentoFinanceiro.Tipo.PAGAR,
            descricao="Conta B vencida",
            valor="900",
            categoria=categoria,
            propriedade=self.propriedade_b,
            safra="2026/2027",
            data_vencimento=timezone.localdate() - timedelta(days=1),
        )
        produto = ProdutoEstoque.objects.create(
            nome="Semente teste",
            categoria=ProdutoEstoque.Categoria.SEMENTE,
            unidade=ProdutoEstoque.Unidade.KG,
            estoque_minimo="0",
        )
        local_a = LocalEstoque.objects.create(
            nome="Depósito A",
            propriedade=self.propriedade_a,
        )
        local_b = LocalEstoque.objects.create(
            nome="Depósito B",
            propriedade=self.propriedade_b,
        )
        self.lote_a = LoteEstoque.objects.create(
            produto=produto,
            local=local_a,
            codigo="A-1",
        )
        self.lote_b = LoteEstoque.objects.create(
            produto=produto,
            local=local_b,
            codigo="B-1",
        )
        self.operacao_a = OperacaoAgricola.objects.create(
            talhao=self.talhao_a,
            tipo=OperacaoAgricola.Tipo.PLANTIO,
            descricao="Plantio A",
            data_planejada=timezone.localdate() + timedelta(days=2),
            area_hectares="10",
            criado_por=self.admin,
        )
        self.operacao_b = OperacaoAgricola.objects.create(
            talhao=self.talhao_b,
            tipo=OperacaoAgricola.Tipo.PLANTIO,
            descricao="Plantio B",
            data_planejada=timezone.localdate() + timedelta(days=2),
            area_hectares="10",
            criado_por=self.superusuario,
        )
        self.maquina_a = Maquina.objects.create(
            identificacao="TR-A",
            tipo=Maquina.Tipo.TRATOR,
            propriedade=self.propriedade_a,
        )
        self.maquina_b = Maquina.objects.create(
            identificacao="TR-B",
            tipo=Maquina.Tipo.TRATOR,
            propriedade=self.propriedade_b,
        )
        self.clima_a = PrevisaoClima.objects.create(
            propriedade=self.propriedade_a,
            data=timezone.localdate(),
            condicao="Estável",
        )
        self.clima_b = PrevisaoClima.objects.create(
            propriedade=self.propriedade_b,
            data=timezone.localdate(),
            condicao="Chuva",
        )

    def autenticar(self, usuario):
        self.client.force_authenticate(usuario)

    def ids(self, resposta):
        dados = resposta.data
        if isinstance(dados, dict) and "results" in dados:
            dados = dados["results"]
        return {item["id"] for item in dados}

    def test_lista_apenas_propriedades_autorizadas(self):
        self.autenticar(self.admin)
        resposta = self.client.get("/api/propriedades/")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(self.ids(resposta), {self.propriedade_a.id})
        self.assertEqual(resposta.data[0]["papel_usuario"], "administrador")

    def test_acesso_direto_de_outra_propriedade_retorna_404(self):
        self.autenticar(self.admin)
        resposta = self.client.get(f"/api/propriedades/{self.propriedade_b.id}/")
        self.assertEqual(resposta.status_code, 404)

    def test_somente_leitura_nao_pode_editar(self):
        self.autenticar(self.leitura)
        resposta = self.client.patch(
            f"/api/propriedades/{self.propriedade_a.id}/",
            {"nome": "Alteração proibida"},
            format="json",
        )
        self.assertEqual(resposta.status_code, 403)

    def test_gestor_pode_editar_propriedade_autorizada(self):
        self.autenticar(self.gestor)
        resposta = self.client.patch(
            f"/api/propriedades/{self.propriedade_a.id}/",
            {"nome": "Fazenda A atualizada"},
            format="json",
        )
        self.assertEqual(resposta.status_code, 200)
        self.propriedade_a.refresh_from_db()
        self.assertEqual(self.propriedade_a.nome, "Fazenda A atualizada")

    def test_operador_executa_operacao_apenas_na_propriedade_autorizada(self):
        self.autenticar(self.operador)
        dados = {
            "talhao": self.talhao_a.id,
            "tipo": OperacaoAgricola.Tipo.PULVERIZACAO,
            "descricao": "Aplicação autorizada",
            "data_planejada": timezone.localdate().isoformat(),
            "area_hectares": "5",
            "custo_estimado": "0",
        }
        resposta = self.client.post(
            "/api/producao/operacoes/",
            dados,
            format="json",
        )
        self.assertEqual(resposta.status_code, 201)

        dados["talhao"] = self.talhao_b.id
        dados["descricao"] = "Aplicação proibida"
        resposta = self.client.post(
            "/api/producao/operacoes/",
            dados,
            format="json",
        )
        self.assertEqual(resposta.status_code, 403)

    def test_admin_pode_vincular_usuario_e_leitura_nao_pode(self):
        novo = get_user_model().objects.create_user("novo_usuario", password="x")
        self.autenticar(self.admin)
        resposta = self.client.post(
            "/api/propriedades/acessos/",
            {
                "propriedade": self.propriedade_a.id,
                "usuario": novo.id,
                "papel": AcessoPropriedade.Papel.LEITURA,
                "ativo": True,
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 201)

        self.autenticar(self.leitura)
        resposta = self.client.post(
            "/api/propriedades/acessos/",
            {
                "propriedade": self.propriedade_a.id,
                "usuario": self.outro.id,
                "papel": AcessoPropriedade.Papel.LEITURA,
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 403)

    def test_modulos_nao_vazam_registros_de_outra_propriedade(self):
        self.autenticar(self.admin)
        casos = (
            ("/api/talhoes/", self.talhao_a.id),
            ("/api/financeiro/lancamentos/", self.financeiro_a.id),
            ("/api/estoque/locais/", self.lote_a.local_id),
            ("/api/estoque/lotes/", self.lote_a.id),
            ("/api/producao/operacoes/", self.operacao_a.id),
            ("/api/maquinas/maquinas/", self.maquina_a.id),
            ("/api/clima/previsoes/", self.clima_a.id),
        )
        for url, esperado in casos:
            with self.subTest(url=url):
                resposta = self.client.get(url)
                self.assertEqual(resposta.status_code, 200)
                self.assertEqual(self.ids(resposta), {esperado})

    def test_dashboard_e_ia_respeitam_escopo_do_usuario(self):
        self.autenticar(self.admin)
        dashboard = self.client.get("/api/relatorios/dashboard/")
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.data["estrutura"]["propriedades"], 1)
        self.assertEqual(dashboard.data["estrutura"]["talhoes"], 1)
        self.assertEqual(dashboard.data["financeiro"]["quantidade_pendente"], 1)
        self.assertEqual(dashboard.data["maquinas"]["total"], 1)

        insights = self.client.get("/api/ai/insights/")
        self.assertEqual(insights.status_code, 200)
        codigos = {item["codigo"] for item in insights.data["insights"]}
        self.assertNotIn("financeiro_atrasado", codigos)

    def test_filtro_manual_de_propriedade_nao_autorizada_retorna_404(self):
        self.autenticar(self.admin)
        for url in (
            f"/api/relatorios/dashboard/?propriedade={self.propriedade_b.id}",
            f"/api/ai/insights/?propriedade={self.propriedade_b.id}",
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)

    def test_superusuario_mantem_acesso_completo(self):
        self.autenticar(self.superusuario)
        resposta = self.client.get("/api/propriedades/")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(
            self.ids(resposta),
            {self.propriedade_a.id, self.propriedade_b.id},
        )

    def test_usuario_sem_vinculo_cria_primeira_propriedade_e_vira_admin(self):
        self.autenticar(self.outro)
        resposta = self.client.post(
            "/api/propriedades/",
            {
                "nome": "Fazenda inicial",
                "municipio": "Ivaiporã",
                "uf": "PR",
                "area_hectares": "10",
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 201)
        acesso = AcessoPropriedade.objects.get(
            usuario=self.outro,
            propriedade_id=resposta.data["id"],
        )
        self.assertEqual(acesso.papel, AcessoPropriedade.Papel.ADMINISTRADOR)

    def test_cadastro_global_exige_perfil_de_gestao(self):
        self.autenticar(self.leitura)
        resposta = self.client.post(
            "/api/financeiro/categorias/",
            {"nome": "Categoria proibida", "aplicacao": "ambos"},
            format="json",
        )
        self.assertEqual(resposta.status_code, 403)

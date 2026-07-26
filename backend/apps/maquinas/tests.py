from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.producao.models import OperacaoAgricola
from apps.propriedades.models import Propriedade
from apps.talhoes.models import Talhao

from .models import Maquina, ManutencaoMaquina
from .services import HorimetroInvalidoError, atualizar_horimetro, concluir_manutencao


class MaquinaBase:
    def criar_dados(self):
        self.usuario = get_user_model().objects.create_user("maquinas", password="x")
        self.propriedade = Propriedade.objects.create(
            nome="Fazenda Máquinas", municipio="Cascavel", uf="PR", area_hectares="100"
        )
        self.talhao = Talhao.objects.create(
            propriedade=self.propriedade, nome="Talhão 1", area_hectares="40"
        )
        self.operacao = OperacaoAgricola.objects.create(
            talhao=self.talhao,
            tipo="plantio",
            descricao="Plantio mecanizado",
            data_planejada=timezone.localdate(),
            area_hectares="40",
            criado_por=self.usuario,
        )
        self.maquina = Maquina.objects.create(
            identificacao="TR-001",
            tipo="trator",
            marca="Modelo",
            propriedade=self.propriedade,
            horimetro_atual="100",
        )


class MaquinaRegrasTests(MaquinaBase, TestCase):
    def setUp(self):
        self.criar_dados()

    def test_horimetro_nao_regride(self):
        with self.assertRaises(HorimetroInvalidoError):
            atualizar_horimetro(self.maquina, "99.9")
        atualizar_horimetro(self.maquina, "101.5")
        self.maquina.refresh_from_db()
        self.assertEqual(self.maquina.horimetro_atual, Decimal("101.5"))

    def test_conclusao_de_manutencao_atualiza_horimetro(self):
        manutencao = ManutencaoMaquina.objects.create(
            maquina=self.maquina,
            descricao="Troca de óleo",
            data_prevista=timezone.localdate(),
        )
        concluida = concluir_manutencao(
            manutencao, horimetro="102", custo="800"
        )
        self.maquina.refresh_from_db()
        self.assertEqual(concluida.status, "concluida")
        self.assertEqual(concluida.custo, Decimal("800"))
        self.assertEqual(self.maquina.horimetro_atual, Decimal("102"))


class MaquinaApiTests(MaquinaBase, APITestCase):
    def setUp(self):
        self.criar_dados()
        self.client.force_authenticate(self.usuario)

    def test_autenticacao(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/maquinas/maquinas/").status_code, 401)

    def test_crud_e_filtros(self):
        criada = self.client.post(
            "/api/maquinas/maquinas/",
            {
                "identificacao": "COL-1",
                "tipo": "colheitadeira",
                "propriedade": self.propriedade.id,
                "horimetro_atual": "20",
            },
            format="json",
        )
        self.assertEqual(criada.status_code, 201, criada.data)
        lista = self.client.get("/api/maquinas/maquinas/?tipo=colheitadeira&search=COL")
        self.assertEqual(len(lista.data), 1)

    def test_uso_vincula_operacao_e_atualiza_horimetro(self):
        resposta = self.client.post(
            "/api/maquinas/usos/",
            {
                "maquina": self.maquina.id,
                "operacao": self.operacao.id,
                "operador": "Carlos",
                "data": str(timezone.localdate()),
                "horimetro_inicial": "100",
                "horimetro_final": "108.5",
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.assertEqual(resposta.data["horas_trabalhadas"], "8.5")
        self.maquina.refresh_from_db()
        self.assertEqual(self.maquina.horimetro_atual, Decimal("108.5"))

    def test_uso_de_maquina_inativa_e_bloqueado(self):
        self.maquina.status = "inativa"
        self.maquina.save(update_fields=("status",))
        resposta = self.client.post(
            "/api/maquinas/usos/",
            {
                "maquina": self.maquina.id,
                "operacao": self.operacao.id,
                "horimetro_inicial": "100",
                "horimetro_final": "101",
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 400)

    def test_abastecimento_atualiza_horimetro_e_e_imutavel(self):
        resposta = self.client.post(
            "/api/maquinas/abastecimentos/",
            {
                "maquina": self.maquina.id,
                "litros": "120",
                "valor_total": "720",
                "horimetro": "103",
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 201)
        url = f"/api/maquinas/abastecimentos/{resposta.data['id']}/"
        self.assertEqual(self.client.patch(url, {"litros": "1"}).status_code, 405)
        self.assertEqual(self.client.delete(url).status_code, 405)

    def test_fluxo_de_manutencao(self):
        agendada = self.client.post(
            "/api/maquinas/manutencoes/",
            {
                "maquina": self.maquina.id,
                "descricao": "Revisão preventiva",
                "data_prevista": str(timezone.localdate()),
                "horimetro_previsto": "105",
            },
            format="json",
        )
        self.assertEqual(agendada.status_code, 201, agendada.data)
        concluida = self.client.post(
            f"/api/maquinas/manutencoes/{agendada.data['id']}/concluir/",
            {
                "data_conclusao": str(timezone.localdate()),
                "horimetro_realizado": "104",
                "custo": "500",
            },
            format="json",
        )
        self.assertEqual(concluida.status_code, 200, concluida.data)
        self.assertEqual(concluida.data["status"], "concluida")
        bloqueada = self.client.patch(
            f"/api/maquinas/manutencoes/{agendada.data['id']}/",
            {"descricao": "Alterada"},
        )
        self.assertEqual(bloqueada.status_code, 409)

    def test_edicao_direta_nao_regride_horimetro(self):
        resposta = self.client.patch(
            f"/api/maquinas/maquinas/{self.maquina.id}/",
            {"horimetro_atual": "90"},
            format="json",
        )
        self.assertEqual(resposta.status_code, 400)

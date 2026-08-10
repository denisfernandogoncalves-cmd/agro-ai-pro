from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.cadpro.models import CADPro, CADProPropriedade
from apps.propriedades.models import Propriedade

from .cargas_services import calcular_peso_liquido, registrar_carga_colhida
from .models import (
    ArmazemGraos,
    CargaColhida,
    GrupoColheita,
    MovimentacaoGraos,
    PosicaoSaldoGraos,
)


class CargaColhidaBase:
    def criar_contexto(self):
        self.usuario = get_user_model().objects.create_user(
            username="operador_colheita",
            password="senha-segura-teste",
        )
        self.propriedade = Propriedade.objects.create(
            nome="Fazenda Modelo",
            municipio="Sorriso",
            uf="MT",
            area_hectares="1000",
        )
        self.cad_pro = CADPro.objects.create(
            codigo="CAD/PRO 123",
            descricao="Titular da produção",
        )
        CADProPropriedade.objects.create(
            cad_pro=self.cad_pro,
            propriedade=self.propriedade,
        )
        self.armazem = ArmazemGraos.objects.create(
            propriedade=self.propriedade,
            nome="Silo Central",
            capacidade_kg="100000.000",
        )
        self.grupo = GrupoColheita.objects.create(
            propriedade=self.propriedade,
            cad_pro=self.cad_pro,
            nome="Equipe Norte",
            cultura="Soja",
            safra="2026/2027",
            tolerancia_umidade_percentual="13.00",
            desconto_umidade_por_ponto="1.000",
            tolerancia_impureza_percentual="1.00",
            desconto_impureza_por_ponto="0.500",
            tolerancia_defeitos_percentual="2.00",
            desconto_defeitos_por_ponto="2.000",
            criado_por=self.usuario,
        )

    def dados_carga(self):
        return {
            "grupo_colheita": self.grupo,
            "armazem": self.armazem,
            "data_colheita": date(2026, 8, 9),
            "placa": "ABC-1D23",
            "peso_bruto_kg": "1000.000",
            "umidade_percentual": "14.00",
            "impureza_percentual": "2.00",
            "defeitos_percentual": "3.00",
            "ph": "78.00",
            "destinado_semente": False,
            "local_colheita": "Talhão Norte",
            "observacoes": "Carga de validação",
        }


class CalculoCargaColhidaTests(CargaColhidaBase, TestCase):
    def setUp(self):
        self.criar_contexto()

    def test_calcula_descontos_peso_liquido_e_sacas(self):
        total, desconto_kg, liquido, sacas, regra = calcular_peso_liquido(
            grupo=self.grupo,
            peso_bruto_kg="1000",
            umidade_percentual="14",
            impureza_percentual="2",
            defeitos_percentual="3",
        )
        self.assertEqual(total, Decimal("3.500"))
        self.assertEqual(desconto_kg, Decimal("35.000"))
        self.assertEqual(liquido, Decimal("965.000"))
        self.assertEqual(sacas, Decimal("16.083"))
        self.assertEqual(regra["parcelas"]["umidade"]["excesso_pontos"], "1.00")

    def test_registro_e_atomico_rastreavel_e_credita_saldo(self):
        carga = registrar_carga_colhida(usuario=self.usuario, **self.dados_carga())

        self.assertEqual(carga.placa, "ABC1D23")
        self.assertEqual(carga.peso_liquido_kg, Decimal("965.000"))
        self.assertEqual(carga.lote.cad_pro, self.cad_pro)
        self.assertEqual(carga.movimentacao.operacao, MovimentacaoGraos.Operacao.CREDITO_PRODUCAO)
        posicao = PosicaoSaldoGraos.objects.get(cad_pro=self.cad_pro)
        self.assertEqual(posicao.saldo_fisico_kg, Decimal("965.000"))
        self.assertEqual(carga.criado_por, self.usuario)

    def test_carga_e_imutavel(self):
        carga = registrar_carga_colhida(usuario=self.usuario, **self.dados_carga())
        carga.observacoes = "Tentativa de alteração"
        with self.assertRaises(ValidationError):
            carga.save()
        with self.assertRaises(ValidationError):
            CargaColhida.objects.filter(pk=carga.pk).update(placa="XYZ9A99")


class CargaColhidaApiTests(CargaColhidaBase, APITestCase):
    def setUp(self):
        self.criar_contexto()
        self.client.force_authenticate(self.usuario)
        self.url = reverse("cargas-colhidas-list")

    def payload(self):
        dados = self.dados_carga()
        dados["grupo_colheita"] = self.grupo.pk
        dados["armazem"] = self.armazem.pk
        dados["data_colheita"] = dados["data_colheita"].isoformat()
        return dados

    def test_cria_lista_e_filtra_carga_manual(self):
        resposta = self.client.post(self.url, self.payload(), format="json")
        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.assertEqual(resposta.data["propriedade_nome"], "Fazenda Modelo")
        self.assertEqual(resposta.data["cad_pro_codigo"], "CAD/PRO 123")
        self.assertEqual(resposta.data["peso_liquido_kg"], "965.000")
        self.assertEqual(resposta.data["sacas_60kg"], "16.083")
        self.assertIsNotNone(resposta.data["movimentacao"])

        listagem = self.client.get(self.url, {"propriedade": self.propriedade.pk})
        self.assertEqual(listagem.status_code, 200)
        self.assertEqual(len(listagem.data), 1)

    def test_bloqueia_duplicidade_sem_duplicar_saldo(self):
        self.assertEqual(self.client.post(self.url, self.payload(), format="json").status_code, 201)
        duplicada = self.client.post(self.url, self.payload(), format="json")
        self.assertEqual(duplicada.status_code, 409)
        self.assertEqual(duplicada.data["codigo"], "carga_colhida_duplicada")
        self.assertEqual(CargaColhida.objects.count(), 1)
        self.assertEqual(MovimentacaoGraos.objects.count(), 1)

    def test_rejeita_armazem_de_outra_propriedade(self):
        outra = Propriedade.objects.create(
            nome="Outra Fazenda",
            municipio="Lucas do Rio Verde",
            uf="MT",
            area_hectares="500",
        )
        armazem = ArmazemGraos.objects.create(
            propriedade=outra,
            nome="Silo Externo",
            capacidade_kg="5000",
        )
        payload = self.payload()
        payload["armazem"] = armazem.pk
        resposta = self.client.post(self.url, payload, format="json")
        self.assertEqual(resposta.status_code, 400)
        self.assertEqual(CargaColhida.objects.count(), 0)
        self.assertEqual(MovimentacaoGraos.objects.count(), 0)

    def test_exige_autenticacao(self):
        self.client.force_authenticate(user=None)
        resposta = self.client.get(self.url)
        self.assertEqual(resposta.status_code, 401)

    def test_api_de_grupos_valida_vinculo_cadpro(self):
        resposta = self.client.post(
            reverse("grupos-colheita-list"),
            {
                "propriedade": self.propriedade.pk,
                "cad_pro": str(self.cad_pro.pk),
                "nome": "Equipe Sul",
                "cultura": "Milho",
                "safra": "2026/2027",
                "tolerancia_umidade_percentual": "14.00",
                "desconto_umidade_por_ponto": "1.000",
                "tolerancia_impureza_percentual": "1.00",
                "desconto_impureza_por_ponto": "1.000",
                "tolerancia_defeitos_percentual": "2.00",
                "desconto_defeitos_por_ponto": "1.000",
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.assertEqual(resposta.data["criado_por"], self.usuario.pk)

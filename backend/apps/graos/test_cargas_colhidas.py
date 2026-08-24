from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import Resolver404, resolve, reverse
from rest_framework.test import APITestCase

from apps.cadpro.models import CADPro, CADProPropriedade
from apps.propriedades.models import Propriedade

from .cargas_services import (
    CargaColhidaError,
    calcular_peso_liquido,
    registrar_carga_colhida,
)
from .models import (
    ArmazemGraos,
    CargaColhida,
    GrupoColheita,
    MovimentacaoGraos,
    PosicaoSaldoGraos,
)
from .services import SaldoGraosError, estornar_movimentacao


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
            armazem_padrao=self.armazem,
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
        self.assertEqual(total, Decimal("2.500"))
        self.assertEqual(desconto_kg, Decimal("25.000"))
        self.assertEqual(liquido, Decimal("975.000"))
        self.assertEqual(sacas, Decimal("16.250"))
        self.assertEqual(regra["parcelas"]["umidade"]["desconto_percentual"], "0")
        self.assertEqual(regra["versao_tabela_umidade"], "2026-08-20")

    def test_tabela_umidade_por_cultura_e_limites(self):
        for cultura, umidade, esperado in (
            ("Soja", "11.5", "0"),
            ("Milho", "30", "24.25"),
            ("Trigo", "13.5", "1"),
            ("Trigo", "30", "25.75"),
        ):
            self.grupo.cultura = cultura
            total, *_ = calcular_peso_liquido(
                grupo=self.grupo,
                peso_bruto_kg="1000",
                umidade_percentual=umidade,
                impureza_percentual="0",
                defeitos_percentual="0",
            )
            self.assertEqual(total, Decimal(esperado))

    def test_rejeita_umidade_fora_da_tabela_ou_entre_passos(self):
        for umidade in ("11", "14.25", "30.5"):
            with self.assertRaises(CargaColhidaError):
                calcular_peso_liquido(
                    grupo=self.grupo,
                    peso_bruto_kg="1000",
                    umidade_percentual=umidade,
                    impureza_percentual="0",
                    defeitos_percentual="0",
                )

    def test_registro_e_atomico_rastreavel_e_credita_saldo(self):
        carga = registrar_carga_colhida(usuario=self.usuario, **self.dados_carga())

        self.assertEqual(carga.placa, "ABC1D23")
        self.assertEqual(carga.peso_liquido_kg, Decimal("975.000"))
        self.assertEqual(carga.lote.cad_pro, self.cad_pro)
        self.assertEqual(carga.movimentacao.operacao, MovimentacaoGraos.Operacao.CREDITO_PRODUCAO)
        posicao = PosicaoSaldoGraos.objects.get(cad_pro=self.cad_pro)
        self.assertEqual(posicao.saldo_fisico_kg, Decimal("975.000"))
        self.assertEqual(carga.criado_por, self.usuario)

    def test_carga_e_imutavel(self):
        carga = registrar_carga_colhida(usuario=self.usuario, **self.dados_carga())
        carga.observacoes = "Tentativa de alteração"
        with self.assertRaises(ValidationError):
            carga.save()
        with self.assertRaises(ValidationError):
            CargaColhida.objects.filter(pk=carga.pk).update(placa="XYZ9A99")

    def test_rateia_multiplas_propriedades_por_area_sem_duplicar(self):
        outra = Propriedade.objects.create(
            nome="Fazenda Associada", municipio="Sorriso", uf="MT",
            area_hectares="500.00",
        )
        CADProPropriedade.objects.create(cad_pro=self.cad_pro, propriedade=outra)
        dados = self.dados_carga()
        dados["propriedades_selecionadas"] = [self.propriedade.pk, outra.pk]
        carga = registrar_carga_colhida(usuario=self.usuario, **dados)
        rateios = carga.contexto_colheita["rateio_producao"]

        self.assertEqual(len(rateios), 2)
        self.assertEqual(
            sum(Decimal(item["peso_liquido_kg"]) for item in rateios),
            carga.peso_liquido_kg,
        )
        self.assertEqual(
            {item["cad_pro_numero"] for item in rateios},
            {self.cad_pro.codigo},
        )
        self.assertEqual(
            {Decimal(item["peso_liquido_kg"]) for item in rateios},
            {Decimal("650.000"), Decimal("325.000")},
        )


class CargaColhidaApiTests(CargaColhidaBase, APITestCase):
    def setUp(self):
        self.criar_contexto()
        self.client.force_authenticate(self.usuario)
        self.url = reverse("cargas-colhidas-list")

    def payload(self):
        dados = self.dados_carga()
        dados.pop("grupo_colheita")
        dados["propriedade"] = self.propriedade.pk
        dados["cad_pro"] = str(self.cad_pro.pk)
        dados["cultura"] = self.grupo.cultura
        dados["safra"] = self.grupo.safra
        dados["armazem"] = self.armazem.pk
        dados["data_colheita"] = dados["data_colheita"].isoformat()
        dados["talhoes_selecionados"] = []
        dados["tolerancia_impureza_percentual"] = "1.00"
        dados["desconto_impureza_por_ponto"] = "0.500"
        dados["tolerancia_defeitos_percentual"] = "2.00"
        dados["desconto_defeitos_por_ponto"] = "2.000"
        return dados

    def test_cria_lista_e_filtra_carga_manual(self):
        resposta = self.client.post(self.url, self.payload(), format="json")
        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.assertEqual(resposta.data["propriedade_nome"], "Fazenda Modelo")
        self.assertEqual(resposta.data["cad_pro_codigo"], "CAD/PRO 123")
        self.assertEqual(resposta.data["peso_liquido_kg"], "975.000")
        self.assertEqual(resposta.data["sacas_60kg"], "16.250")
        self.assertEqual(resposta.data["status"], "ativa")
        self.assertNotIn("grupo_colheita", resposta.data)
        self.assertEqual(
            resposta.data["contexto_colheita"]["area_total_propriedades_hectares"],
            "1000.00",
        )
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

    def test_aceita_motorista_sem_placa(self):
        payload = self.payload()
        payload["placa"] = ""
        payload["motorista"] = "  João da Silva  "
        resposta = self.client.post(self.url, payload, format="json")
        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.assertEqual(resposta.data["motorista"], "João da Silva")
        self.assertEqual(resposta.data["placa"], "")

    def test_rota_operacional_de_grupos_foi_removida(self):
        with self.assertRaises(Resolver404):
            resolve("/api/graos/grupos-colheita/")

    def test_edita_por_substituicao_atomica_e_recalcula_saldo(self):
        criada = self.client.post(self.url, self.payload(), format="json")
        self.assertEqual(criada.status_code, 201, criada.data)
        carga_id = criada.data["id"]
        payload = self.payload()
        payload["peso_bruto_kg"] = "900.000"
        payload["observacoes"] = "Peso corrigido"

        resposta = self.client.patch(
            reverse("cargas-colhidas-detail", args=(carga_id,)),
            payload,
            format="json",
        )

        self.assertEqual(resposta.status_code, 200, resposta.data)
        self.assertNotEqual(resposta.data["id"], carga_id)
        original = CargaColhida.objects.get(pk=carga_id)
        self.assertEqual(original.status, CargaColhida.Status.SUBSTITUIDA)
        self.assertEqual(original.substituida_por_id, resposta.data["id"])
        self.assertEqual(resposta.data["peso_liquido_kg"], "877.500")
        self.assertEqual(
            PosicaoSaldoGraos.objects.get(cad_pro=self.cad_pro).saldo_fisico_kg,
            Decimal("877.500"),
        )
        self.assertEqual(MovimentacaoGraos.objects.count(), 3)

        repetida = self.client.patch(
            reverse("cargas-colhidas-detail", args=(carga_id,)),
            {**payload, "peso_bruto_kg": "800.000"},
            format="json",
        )
        self.assertEqual(repetida.status_code, 400, repetida.data)
        self.assertEqual(CargaColhida.objects.count(), 2)
        self.assertEqual(MovimentacaoGraos.objects.count(), 3)
        self.assertEqual(
            PosicaoSaldoGraos.objects.get(cad_pro=self.cad_pro).saldo_fisico_kg,
            Decimal("877.500"),
        )

        cancelamento_antigo = self.client.delete(
            reverse("cargas-colhidas-detail", args=(carga_id,)),
        )
        self.assertEqual(cancelamento_antigo.status_code, 409)
        self.assertEqual(
            cancelamento_antigo.data["substituida_por"],
            resposta.data["id"],
        )
        self.assertEqual(CargaColhida.objects.count(), 2)
        self.assertEqual(MovimentacaoGraos.objects.count(), 3)

    def test_bloqueia_estorno_generico_de_movimentacao_de_carga(self):
        criada = self.client.post(self.url, self.payload(), format="json")
        self.assertEqual(criada.status_code, 201, criada.data)
        carga = CargaColhida.objects.get(pk=criada.data["id"])

        with self.assertRaises(SaldoGraosError):
            estornar_movimentacao(
                usuario=self.usuario,
                movimentacao=carga.movimentacao,
                chave_idempotencia=f"teste-estorno-generico-carga:{carga.pk}",
            )

        carga.refresh_from_db()
        self.assertEqual(carga.status, CargaColhida.Status.ATIVA)
        self.assertEqual(MovimentacaoGraos.objects.count(), 1)
        self.assertEqual(
            PosicaoSaldoGraos.objects.get(cad_pro=self.cad_pro).saldo_fisico_kg,
            Decimal("975.000"),
        )

    def test_chaves_distintas_permite_viagens_reais_com_mesmos_dados(self):
        primeira = self.payload()
        primeira["chave_registro"] = "viagem-real-00000001"
        self.assertEqual(self.client.post(self.url, primeira, format="json").status_code, 201)

        repetida = self.client.post(self.url, primeira, format="json")
        self.assertEqual(repetida.status_code, 409)

        segunda = {**primeira, "chave_registro": "viagem-real-00000002"}
        self.assertEqual(self.client.post(self.url, segunda, format="json").status_code, 201)
        self.assertEqual(CargaColhida.objects.count(), 2)
        self.assertEqual(MovimentacaoGraos.objects.count(), 2)
        self.assertEqual(
            PosicaoSaldoGraos.objects.get(cad_pro=self.cad_pro).saldo_fisico_kg,
            Decimal("1950.000"),
        )

    def test_exclui_por_cancelamento_auditavel_e_estorno_idempotente(self):
        criada = self.client.post(self.url, self.payload(), format="json")
        self.assertEqual(criada.status_code, 201, criada.data)
        detalhe = reverse("cargas-colhidas-detail", args=(criada.data["id"],))

        self.assertEqual(self.client.delete(detalhe).status_code, 204)
        self.assertEqual(self.client.delete(detalhe).status_code, 204)

        carga = CargaColhida.objects.get(pk=criada.data["id"])
        self.assertEqual(carga.status, CargaColhida.Status.CANCELADA)
        self.assertIsNotNone(carga.cancelada_em)
        self.assertEqual(carga.cancelada_por, self.usuario)
        self.assertEqual(
            PosicaoSaldoGraos.objects.get(cad_pro=self.cad_pro).saldo_fisico_kg,
            Decimal("0.000"),
        )
        self.assertEqual(MovimentacaoGraos.objects.count(), 2)
        ativas = self.client.get(self.url, {"status": "ativa"})
        self.assertEqual(ativas.status_code, 200)
        self.assertEqual(ativas.data, [])

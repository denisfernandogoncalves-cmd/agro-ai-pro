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
    OrigemSaldoGraos,
    PosicaoSaldoGraos,
    RateioCargaColhida,
)
from .services import SaldoGraosError, estornar_movimentacao, reservar_saldo


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

    def test_exemplo_planilha_desconta_impureza_e_avariados_integralmente(self):
        total, desconto, liquido, sacas, regra = calcular_peso_liquido(
            cultura="Soja", peso_bruto_kg="1000", umidade_percentual="13",
            impureza_percentual="1", defeitos_percentual="1",
        )
        self.assertEqual((total, desconto, liquido, sacas), (
            Decimal("2.000"), Decimal("20.000"), Decimal("980.000"), Decimal("16.333"),
        ))
        self.assertEqual(regra["peso_apos_umidade_kg"], "1000.000")

    def test_classificacao_acumulada_sobre_peso_apos_umidade(self):
        total, desconto, liquido, sacas, regra = calcular_peso_liquido(
            cultura="Soja", peso_bruto_kg="10000", umidade_percentual="20.5",
            impureza_percentual="2", defeitos_percentual="3",
        )
        self.assertEqual((total, desconto, liquido, sacas), (
            Decimal("14.500"), Decimal("1450.000"), Decimal("8550.000"), Decimal("142.500"),
        ))
        self.assertEqual(regra["parcelas"]["impureza"]["base_kg"], "9000.000")
        self.assertEqual(regra["parcelas"]["defeitos"]["base_kg"], "9000.000")
        self.assertEqual(regra["desconto_classificacao_kg"], "450.000")

    def test_rejeita_classificacao_acumulada_de_cem_porcento(self):
        with self.assertRaises(CargaColhidaError):
            calcular_peso_liquido(
                cultura="Soja", peso_bruto_kg="1000", umidade_percentual="20.5",
                impureza_percentual="50", defeitos_percentual="50",
            )

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
        self.assertEqual(RateioCargaColhida.objects.filter(carga=carga).count(), 2)
        self.assertEqual(
            sum(
                RateioCargaColhida.objects.filter(carga=carga).values_list(
                    "peso_liquido_kg", flat=True
                )
            ),
            carga.peso_liquido_kg,
        )
        posicoes = PosicaoSaldoGraos.objects.filter(
            cad_pro=self.cad_pro,
        ).order_by("propriedade_id")
        self.assertEqual(posicoes.count(), 2)
        self.assertEqual(
            {
                item.propriedade_id: item.saldo_fisico_kg
                for item in posicoes
            },
            {
                self.propriedade.pk: Decimal("650.000"),
                outra.pk: Decimal("325.000"),
            },
        )

    def test_rateia_e_credita_o_saldo_de_cada_cadpro(self):
        outra = Propriedade.objects.create(
            nome="Fazenda Associada", municipio="Sorriso", uf="MT",
            area_hectares="500.00",
        )
        outro_cadpro = CADPro.objects.create(
            codigo="CAD/PRO 456",
            descricao="Titular da propriedade associada",
        )
        CADProPropriedade.objects.create(cad_pro=self.cad_pro, propriedade=outra)
        CADProPropriedade.objects.create(cad_pro=outro_cadpro, propriedade=outra)
        dados = self.dados_carga()
        dados["propriedades_selecionadas"] = [self.propriedade.pk, outra.pk]
        dados["cadpros_por_propriedade"] = {
            str(self.propriedade.pk): str(self.cad_pro.pk),
            str(outra.pk): str(outro_cadpro.pk),
        }

        carga = registrar_carga_colhida(usuario=self.usuario, **dados)

        self.assertEqual(
            PosicaoSaldoGraos.objects.get(cad_pro=self.cad_pro).saldo_fisico_kg,
            Decimal("650.000"),
        )
        self.assertEqual(
            PosicaoSaldoGraos.objects.get(cad_pro=outro_cadpro).saldo_fisico_kg,
            Decimal("325.000"),
        )
        self.assertEqual(
            set(
                RateioCargaColhida.objects.filter(carga=carga).values_list(
                    "cad_pro_id", "peso_liquido_kg"
                )
            ),
            {
                (self.cad_pro.pk, Decimal("650.000")),
                (outro_cadpro.pk, Decimal("325.000")),
            },
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
        dados["propriedades_selecionadas"] = [self.propriedade.pk]
        dados["cadpros_por_propriedade"] = {
            str(self.propriedade.pk): str(self.cad_pro.pk),
        }
        dados["tolerancia_impureza_percentual"] = "1.00"
        dados["desconto_impureza_por_ponto"] = "0.500"
        dados["tolerancia_defeitos_percentual"] = "2.00"
        dados["desconto_defeitos_por_ponto"] = "2.000"
        return dados

    def test_api_aplica_desconto_integral_padrao_e_credita_liquido(self):
        dados = self.payload()
        for chave in ("tolerancia_impureza_percentual", "tolerancia_defeitos_percentual",
                      "desconto_impureza_por_ponto", "desconto_defeitos_por_ponto"):
            dados.pop(chave)
        dados.update(umidade_percentual="13", impureza_percentual="1", defeitos_percentual="1")
        resposta = self.client.post(self.url, dados, format="json")
        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.assertEqual(resposta.data["peso_liquido_kg"], "980.000")
        self.assertEqual(PosicaoSaldoGraos.objects.get(cad_pro=self.cad_pro).saldo_fisico_kg, Decimal("980"))

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

    def test_aceita_armazenagem_externa_sem_propriedade(self):
        armazem = ArmazemGraos.objects.create(
            nome="Silo Externo",
            capacidade_kg="5000",
        )
        payload = self.payload()
        payload["armazem"] = armazem.pk
        resposta = self.client.post(self.url, payload, format="json")
        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.assertEqual(resposta.data["propriedade"], self.propriedade.pk)
        self.assertEqual(resposta.data["armazem"], armazem.pk)
        self.assertEqual(CargaColhida.objects.count(), 1)
        self.assertEqual(MovimentacaoGraos.objects.count(), 1)

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

    def _criar_carga_rateada(self):
        outra = Propriedade.objects.create(
            nome="Fazenda Secundária", municipio="Sorriso", uf="MT",
            area_hectares="500.00",
        )
        outro_cadpro = CADPro.objects.create(
            codigo="CAD-RATEIO-SECUNDARIO", descricao="Titular da parcela secundária",
        )
        CADProPropriedade.objects.create(cad_pro=outro_cadpro, propriedade=outra)
        dados = self.payload()
        dados["propriedades_selecionadas"].append(outra.pk)
        dados["cadpros_por_propriedade"][str(outra.pk)] = str(outro_cadpro.pk)
        resposta = self.client.post(self.url, dados, format="json")
        self.assertEqual(resposta.status_code, 201, resposta.data)
        carga = CargaColhida.objects.get(pk=resposta.data["id"])
        return carga, carga.rateios.get(propriedade=outra)

    def test_bloqueia_estorno_generico_de_todas_as_parcelas_pelas_duas_rotas(self):
        carga, secundaria = self._criar_carga_rateada()
        saldos = list(PosicaoSaldoGraos.objects.order_by("pk").values_list("saldo_fisico_kg", flat=True))
        origens = OrigemSaldoGraos.objects.count()
        for movimento_id in (carga.movimentacao_id, secundaria.movimentacao_id):
            rotas = (
                reverse("movimentacoes-graos-estornar", args=(movimento_id,)),
                reverse("saldos-graos-estornar-movimentacao"),
            )
            for indice, rota in enumerate(rotas):
                with self.subTest(movimento=movimento_id, rota=rota):
                    resposta = self.client.post(rota, {
                        "movimentacao": movimento_id,
                        "chave_idempotencia": f"estorno-parcela:{movimento_id}:{indice}",
                        "permitir_carga_colhida": True,
                    }, format="json")
                    self.assertEqual(resposta.status_code, 409, resposta.data)
                    self.assertIn("pela própria carga", str(resposta.data))
        carga.refresh_from_db()
        self.assertEqual(carga.status, CargaColhida.Status.ATIVA)
        self.assertEqual(MovimentacaoGraos.objects.count(), 2)
        self.assertEqual(OrigemSaldoGraos.objects.count(), origens)
        self.assertEqual(list(PosicaoSaldoGraos.objects.order_by("pk").values_list("saldo_fisico_kg", flat=True)), saldos)

    def test_cancelamento_rateado_estorna_todas_as_parcelas_uma_unica_vez(self):
        carga, _ = self._criar_carga_rateada()
        detalhe = reverse("cargas-colhidas-detail", args=(carga.pk,))
        self.assertEqual(self.client.delete(detalhe).status_code, 204)
        self.assertEqual(self.client.delete(detalhe).status_code, 204)
        carga.refresh_from_db()
        self.assertEqual(carga.status, CargaColhida.Status.CANCELADA)
        self.assertEqual(carga.rateios.count(), 2)
        self.assertEqual(MovimentacaoGraos.objects.count(), 4)
        self.assertEqual(set(PosicaoSaldoGraos.objects.values_list("saldo_fisico_kg", flat=True)), {Decimal("0")})

    def test_correcao_rateada_substitui_todas_as_parcelas(self):
        carga, _ = self._criar_carga_rateada()
        resposta = self.client.patch(
            reverse("cargas-colhidas-detail", args=(carga.pk,)),
            {"peso_bruto_kg": "900.000"}, format="json",
        )
        self.assertEqual(resposta.status_code, 200, resposta.data)
        carga.refresh_from_db()
        self.assertEqual(carga.status, CargaColhida.Status.SUBSTITUIDA)
        self.assertEqual(carga.substituida_por_id, resposta.data["id"])
        self.assertEqual(carga.substituida_por.rateios.count(), 2)
        self.assertEqual(MovimentacaoGraos.objects.count(), 6)
        self.assertEqual(set(PosicaoSaldoGraos.objects.values_list("saldo_fisico_kg", flat=True)), {Decimal("585.000"), Decimal("292.500")})

    def test_cancelamento_e_correcao_com_parcela_reservada_nao_estornam_parcialmente(self):
        carga, secundaria = self._criar_carga_rateada()
        reservar_saldo(usuario=self.usuario, lote=secundaria.lote, quantidade_kg="1.000", chave_idempotencia="reserva-parcela")
        saldos = list(PosicaoSaldoGraos.objects.order_by("pk").values_list("saldo_fisico_kg", "saldo_comprometido_kg"))
        movimentos = MovimentacaoGraos.objects.count()
        origens = OrigemSaldoGraos.objects.count()
        detalhe = reverse("cargas-colhidas-detail", args=(carga.pk,))
        for metodo in ("delete", "patch"):
            with self.subTest(metodo=metodo):
                resposta = getattr(self.client, metodo)(detalhe, {"peso_bruto_kg": "900.000"}, format="json")
                self.assertEqual(resposta.status_code, 409, resposta.data)
                carga.refresh_from_db()
                self.assertEqual(carga.status, CargaColhida.Status.ATIVA)
                self.assertIsNone(carga.substituida_por_id)
                self.assertEqual(CargaColhida.objects.count(), 1)
                self.assertEqual(MovimentacaoGraos.objects.count(), movimentos)
                self.assertEqual(OrigemSaldoGraos.objects.count(), origens)
                self.assertEqual(list(PosicaoSaldoGraos.objects.order_by("pk").values_list("saldo_fisico_kg", "saldo_comprometido_kg")), saldos)

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

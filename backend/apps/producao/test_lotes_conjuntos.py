from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.estoque.models import LocalEstoque
from apps.propriedades.models import AcessoPropriedade, Propriedade
from apps.talhoes.models import Talhao

from .grain_models import AcessoCadPro, AuditoriaProducao, CadPro, Cultura, Motorista, Safra, SaldoGraos, Veiculo
from .grain_services import ProducaoError
from .joint_models import (
    CargaLoteConjunto,
    LoteConjuntoProducao,
    MovimentacaoLoteConjunto,
    ParticipanteLoteConjunto,
    SaidaLoteConjunto,
    SaldoLoteConjunto,
    TalhaoParticipanteLoteConjunto,
)
from .joint_services import (
    confirmar_lote,
    confirmar_saida_conjunta,
    estornar_saida_conjunta,
    lotes_conjuntos_visiveis,
    ratear_manual,
    recalcular_lote,
    resumo_transportes,
)


@override_settings(PROPERTY_ACCESS_LEGACY_TEST_MODE=False)
class LotesConjuntosProducaoTests(APITestCase):
    def setUp(self):
        usuario = get_user_model()
        self.admin = usuario.objects.create_user(username="admin-conjunto", password="teste")
        self.gestor = usuario.objects.create_user(username="gestor-conjunto", password="teste")
        self.operador = usuario.objects.create_user(username="operador-conjunto", password="teste")
        self.leitor = usuario.objects.create_user(username="leitor-conjunto", password="teste")
        self.externo = usuario.objects.create_user(username="externo-conjunto", password="teste")

        self.propriedade_a = Propriedade.objects.create(
            nome="Fazenda A",
            proprietario="Produtor A",
            municipio="Ivaiporã",
            uf="PR",
            area_hectares="100.00",
        )
        self.propriedade_b = Propriedade.objects.create(
            nome="Fazenda B",
            proprietario="Produtor B",
            municipio="Arapuã",
            uf="PR",
            area_hectares="80.00",
        )
        self.propriedade_c = Propriedade.objects.create(
            nome="Fazenda C",
            proprietario="Produtor C",
            municipio="Jardim Alegre",
            uf="PR",
            area_hectares="60.00",
        )
        for propriedade in (self.propriedade_a, self.propriedade_b, self.propriedade_c):
            AcessoPropriedade.objects.create(
                propriedade=propriedade,
                usuario=self.admin,
                papel=AcessoPropriedade.Papel.ADMINISTRADOR,
            )
            AcessoPropriedade.objects.create(
                propriedade=propriedade,
                usuario=self.gestor,
                papel=AcessoPropriedade.Papel.GESTOR,
            )
            AcessoPropriedade.objects.create(
                propriedade=propriedade,
                usuario=self.operador,
                papel=AcessoPropriedade.Papel.OPERADOR,
            )
            AcessoPropriedade.objects.create(
                propriedade=propriedade,
                usuario=self.leitor,
                papel=AcessoPropriedade.Papel.LEITURA,
            )
        AcessoPropriedade.objects.create(
            propriedade=self.propriedade_a,
            usuario=self.externo,
            papel=AcessoPropriedade.Papel.GESTOR,
        )

        self.cadpro_a = CadPro.objects.create(propriedade=self.propriedade_a, codigo="CAD-A", titular="Produtor A")
        self.cadpro_b = CadPro.objects.create(propriedade=self.propriedade_b, codigo="CAD-B", titular="Produtor B")
        self.cadpro_c = CadPro.objects.create(propriedade=self.propriedade_c, codigo="CAD-C", titular="Produtor C")
        for cadpro in (self.cadpro_a, self.cadpro_b, self.cadpro_c):
            for pessoa in (self.admin, self.gestor, self.operador, self.leitor):
                AcessoCadPro.objects.create(cadpro=cadpro, usuario=pessoa)
        AcessoCadPro.objects.create(cadpro=self.cadpro_a, usuario=self.externo)

        self.cultura = Cultura.objects.create(nome="Soja lote conjunto", codigo="soja-conjunto", peso_saca_kg="60")
        self.safra = Safra.objects.create(nome="2026/2027 conjunto")
        self.local = LocalEstoque.objects.create(nome="Silo compartilhado")
        self.local_destino = LocalEstoque.objects.create(nome="Armazém compartilhado")
        self.talhao_a = Talhao.objects.create(
            propriedade=self.propriedade_a,
            nome="Talhão A",
            area_hectares="40.00",
            cultura_atual="Soja",
            safra="2026/2027",
        )
        self.talhao_b = Talhao.objects.create(
            propriedade=self.propriedade_b,
            nome="Talhão B",
            area_hectares="30.00",
            cultura_atual="Soja",
            safra="2026/2027",
        )
        self.motorista = Motorista.objects.create(nome="Motorista Teste", documento="12345678901")
        self.veiculo = Veiculo.objects.create(placa="ABC1D23", motorista_padrao=self.motorista)

    def criar_lote(self, modo=LoteConjuntoProducao.ModoRateio.SEM_RATEIO, tres=False):
        lote = LoteConjuntoProducao.objects.create(
            descricao="Colheita não separada",
            cultura=self.cultura,
            safra=self.safra,
            data_inicio_colheita="2026-07-20",
            local_armazenagem=self.local,
            modo_rateio=modo,
            criado_por=self.gestor,
        )
        participante_a = ParticipanteLoteConjunto.objects.create(
            lote=lote,
            propriedade=self.propriedade_a,
            cadpro=self.cadpro_a,
            area_cadastrada_ha="40.0000",
            area_colhida_ha="30.0000",
        )
        participante_b = ParticipanteLoteConjunto.objects.create(
            lote=lote,
            propriedade=self.propriedade_b,
            cadpro=self.cadpro_b,
            area_cadastrada_ha="30.0000",
            area_colhida_ha="20.0000",
        )
        TalhaoParticipanteLoteConjunto.objects.create(
            participante=participante_a,
            talhao=self.talhao_a,
            area_cadastrada_ha="40.0000",
            area_colhida_ha="30.0000",
        )
        TalhaoParticipanteLoteConjunto.objects.create(
            participante=participante_b,
            talhao=self.talhao_b,
            area_cadastrada_ha="30.0000",
            area_colhida_ha="20.0000",
        )
        if tres:
            ParticipanteLoteConjunto.objects.create(
                lote=lote,
                propriedade=self.propriedade_c,
                cadpro=self.cadpro_c,
                area_cadastrada_ha="60.0000",
                area_colhida_ha="10.0000",
            )
        CargaLoteConjunto.objects.create(
            lote=lote,
            motorista=self.motorista,
            veiculo_cavalo=self.veiculo,
            local_armazenagem=self.local,
            romaneio="ROM-001",
            peso_bruto_kg="23000.000",
            tara_kg="3000.000",
            peso_liquido_kg="20000.000",
            umidade_percentual="13.000",
            impureza_percentual="1.000",
            defeitos_percentual="0.500",
            criado_por=self.operador,
        )
        return recalcular_lote(lote)

    def test_api_cria_lote_com_duas_propriedades_e_areas_parciais(self):
        self.client.force_authenticate(self.gestor)
        resposta = self.client.post(
            "/api/producao/lotes-conjuntos/",
            {
                "descricao": "Lote API",
                "cultura": self.cultura.pk,
                "safra": self.safra.pk,
                "data_inicio_colheita": "2026-07-20",
                "local_armazenagem": self.local.pk,
                "modo_rateio": "sem_rateio",
                "participantes": [
                    {
                        "propriedade": self.propriedade_a.pk,
                        "cadpro": self.cadpro_a.pk,
                        "area_cadastrada_ha": "40.0000",
                        "area_colhida_ha": "25.0000",
                        "talhoes": [{"talhao": self.talhao_a.pk, "area_cadastrada_ha": "40.0000", "area_colhida_ha": "25.0000"}],
                    },
                    {
                        "propriedade": self.propriedade_b.pk,
                        "cadpro": self.cadpro_b.pk,
                        "area_cadastrada_ha": "30.0000",
                        "area_colhida_ha": "15.0000",
                        "talhoes": [{"talhao": self.talhao_b.pk, "area_cadastrada_ha": "30.0000", "area_colhida_ha": "15.0000"}],
                    },
                ],
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED, resposta.data)
        self.assertEqual(resposta.data["area_total_colhida_ha"], "40.0000")
        self.assertEqual(len(resposta.data["participantes"]), 2)
        self.assertTrue(resposta.data["codigo"].startswith("LC-"))

    def test_criacao_com_varias_propriedades_soma_areas(self):
        lote = self.criar_lote(tres=True)
        self.assertEqual(lote.participantes.count(), 3)
        self.assertEqual(lote.area_total_cadastrada_ha, Decimal("130.0000"))
        self.assertEqual(lote.area_total_colhida_ha, Decimal("60.0000"))
        self.assertEqual(lote.produtividade_kg_ha.quantize(Decimal("0.001")), Decimal("333.333"))

    def test_area_superior_exige_admin_e_justificativa(self):
        self.client.force_authenticate(self.gestor)
        resposta = self.client.post(
            "/api/producao/lotes-conjuntos/",
            {
                "cultura": self.cultura.pk,
                "safra": self.safra.pk,
                "data_inicio_colheita": "2026-07-20",
                "local_armazenagem": self.local.pk,
                "participantes": [
                    {"propriedade": self.propriedade_a.pk, "cadpro": self.cadpro_a.pk, "area_cadastrada_ha": "10", "area_colhida_ha": "12", "justificativa_excesso_area": "Medição revisada"},
                    {"propriedade": self.propriedade_b.pk, "cadpro": self.cadpro_b.pk, "area_cadastrada_ha": "10", "area_colhida_ha": "10"},
                ],
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)

    def test_confirmacao_sem_rateio_mantem_saldo_conjunto(self):
        lote = confirmar_lote(self.criar_lote(), usuario=self.gestor)
        saldo = SaldoLoteConjunto.objects.get(lote=lote, local_armazenagem=self.local)
        self.assertEqual(lote.status, LoteConjuntoProducao.Status.CONFIRMADO)
        self.assertEqual(saldo.quantidade_kg, Decimal("20000.000"))
        self.assertFalse(SaldoGraos.objects.filter(cultura=self.cultura, safra=self.safra).exists())
        self.assertEqual(lote.quantidade_sacas.quantize(Decimal("0.001")), Decimal("333.333"))

    def test_rateio_automatico_area_preserva_total_e_identifica_estimativa(self):
        lote = confirmar_lote(self.criar_lote(modo=LoteConjuntoProducao.ModoRateio.AREA), usuario=self.gestor)
        participantes = list(lote.participantes.order_by("propriedade__nome"))
        self.assertEqual(participantes[0].quantidade_rateada_kg, Decimal("12000.000"))
        self.assertEqual(participantes[1].quantidade_rateada_kg, Decimal("8000.000"))
        self.assertEqual(participantes[0].metodo_rateio, ParticipanteLoteConjunto.MetodoRateio.AREA)
        self.assertEqual(sum(SaldoGraos.objects.filter(cultura=self.cultura).values_list("quantidade_kg", flat=True)), Decimal("20000.000"))
        self.assertEqual(sum(lote.saldos_conjuntos.values_list("quantidade_kg", flat=True)), Decimal("0.000"))

    def test_rateio_manual_divergente_e_bloqueado_e_aceita_multiplos_cadpro(self):
        lote = confirmar_lote(self.criar_lote(), usuario=self.gestor)
        participantes = list(lote.participantes.order_by("propriedade__nome"))
        with self.assertRaises(ProducaoError):
            ratear_manual(
                lote,
                usuario=self.gestor,
                itens=[
                    {"participante": participantes[0].pk, "cadpro": self.cadpro_a.pk, "quantidade": "100", "unidade": "sacas"},
                    {"participante": participantes[1].pk, "cadpro": self.cadpro_b.pk, "quantidade": "100", "unidade": "sacas"},
                ],
                justificativa="Apuração de balança",
            )
        ratear_manual(
            lote,
            usuario=self.gestor,
            itens=[
                {"participante": participantes[0].pk, "cadpro": self.cadpro_a.pk, "quantidade": "12", "unidade": "toneladas"},
                {"participante": participantes[1].pk, "cadpro": self.cadpro_b.pk, "quantidade": "8000", "unidade": "kg"},
            ],
            justificativa="Divisão conferida pelo responsável",
        )
        self.assertEqual(lote.cadpros_participantes.count(), 2)
        self.assertEqual(sum(lote.cadpros_participantes.values_list("quantidade_atribuida_kg", flat=True)), Decimal("20000.000"))

    def test_saida_parcial_total_saldo_negativo_e_estorno(self):
        lote = confirmar_lote(self.criar_lote(), usuario=self.gestor)
        saida = SaidaLoteConjunto.objects.create(
            lote=lote,
            local_armazenagem=self.local,
            romaneio="SAI-001",
            quantidade_kg="5000.000",
            criado_por=self.operador,
        )
        confirmar_saida_conjunta(saida, usuario=self.operador)
        saldo = SaldoLoteConjunto.objects.get(lote=lote, local_armazenagem=self.local)
        self.assertEqual(saldo.quantidade_kg, Decimal("15000.000"))
        saida_total = SaidaLoteConjunto.objects.create(
            lote=lote,
            local_armazenagem=self.local,
            romaneio="SAI-002",
            quantidade_kg="15000.000",
            criado_por=self.operador,
        )
        confirmar_saida_conjunta(saida_total, usuario=self.operador)
        saldo.refresh_from_db()
        self.assertEqual(saldo.quantidade_kg, Decimal("0.000"))
        excedente = SaidaLoteConjunto.objects.create(
            lote=lote,
            local_armazenagem=self.local,
            romaneio="SAI-003",
            quantidade_kg="1.000",
            criado_por=self.operador,
        )
        with self.assertRaises(ProducaoError):
            confirmar_saida_conjunta(excedente, usuario=self.operador)
        estornar_saida_conjunta(saida, usuario=self.admin, motivo="Romaneio cancelado")
        saldo.refresh_from_db()
        self.assertEqual(saldo.quantidade_kg, Decimal("5000.000"))

    def test_multiplas_cargas_total_motorista_placa_e_media(self):
        lote = self.criar_lote()
        CargaLoteConjunto.objects.create(
            lote=lote,
            motorista=self.motorista,
            placa_cavalo_informada="abc-1d23",
            local_armazenagem=self.local,
            romaneio="ROM-002",
            peso_bruto_kg="13000",
            tara_kg="3000",
            peso_liquido_kg="10000",
            criado_por=self.operador,
        )
        lote = recalcular_lote(lote)
        resumo = resumo_transportes(lote)
        self.assertEqual(lote.peso_liquido_total_kg, Decimal("30000.000"))
        self.assertEqual(resumo["quantidade_cargas"], 2)
        self.assertEqual(resumo["peso_medio_kg"], Decimal("15000.000"))
        self.assertEqual(resumo["por_motorista"][0]["viagens"], 2)

    def test_permissoes_isolamento_e_auditoria(self):
        lote = self.criar_lote()
        self.assertFalse(lotes_conjuntos_visiveis(self.externo).filter(pk=lote.pk).exists())
        self.client.force_authenticate(self.externo)
        self.assertEqual(self.client.get(f"/api/producao/lotes-conjuntos/{lote.pk}/").status_code, status.HTTP_404_NOT_FOUND)
        self.client.force_authenticate(self.leitor)
        self.assertEqual(self.client.post(f"/api/producao/lotes-conjuntos/{lote.pk}/confirmar/").status_code, status.HTTP_403_FORBIDDEN)
        confirmar_lote(lote, usuario=self.gestor)
        self.assertTrue(AuditoriaProducao.objects.filter(acao="lote_conjunto_confirmado").exists())
        movimento = MovimentacaoLoteConjunto.objects.get(lote=lote, tipo=MovimentacaoLoteConjunto.Tipo.ENTRADA)
        self.assertEqual(movimento.saldo_destino_anterior, Decimal("0"))
        self.assertEqual(movimento.saldo_destino_posterior, Decimal("20000.000"))

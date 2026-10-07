from decimal import Decimal
from io import BytesIO
from uuid import uuid4

from django.db.models import Sum
from django.urls import reverse
from openpyxl import load_workbook
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import AcessoUsuario
from .cargas_services import registrar_carga_colhida
from .models import CargaColhida, EntradaProducaoTerceiro, MovimentacaoGraos, PosicaoSaldoGraos
from .services import reservar_saldo
from .test_cargas_colhidas import CargaColhidaBase


class ConferenciaResumoTests(CargaColhidaBase, APITestCase):
    def setUp(self):
        self.criar_contexto()
        self.client.force_authenticate(self.usuario)
        self.dados = {"depositante": "Produtor externo", "cultura": "Soja", "safra": "2026", "armazem": self.armazem.pk, "peso_total_kg": "1500", "tara_kg": "500", "peso_bruto_kg": "1000", "umidade_percentual": "13", "impureza_percentual": "1", "defeitos_percentual": "1", "data_entrada": "2026-10-07", "placa": "ABC1D23"}
        self.previa = reverse("conferencia-pesagem")

    def entrada(self, **mudancas):
        resposta = self.client.post(reverse("terceiros-entradas"), {**self.dados, **mudancas}, format="json", HTTP_IDEMPOTENCY_KEY=str(uuid4()))
        self.assertEqual(resposta.status_code, 201, resposta.data)
        return resposta.data

    def operar(self, nome, pk, dados):
        resposta = self.client.post(reverse(nome, args=(pk,)), dados, format="json", HTTP_IDEMPOTENCY_KEY=str(uuid4()))
        self.assertEqual(resposta.status_code, 201, resposta.data)
        return resposta.data

    def conferir(self, **mudancas):
        return self.client.post(self.previa, {**self.dados, "origem": "terceiro", **mudancas}, format="json")

    def test_previa_calcula_equacao_sem_movimentar(self):
        resposta = self.conferir(peso_bruto_kg="9999")
        self.assertEqual(resposta.status_code, 200, resposta.data)
        self.assertEqual(Decimal(resposta.data["peso_bruto_kg"]), Decimal(1000))
        self.assertEqual(Decimal(resposta.data["desconto_total_kg"]), Decimal(20))
        self.assertEqual(Decimal(resposta.data["peso_liquido_kg"]), Decimal(980))
        self.assertEqual(resposta.data["alertas"], [])
        self.assertEqual(EntradaProducaoTerceiro.objects.count(), 0)
        self.assertEqual(MovimentacaoGraos.objects.count(), 0)
        self.assertEqual(self.conferir(tara_kg="1500").status_code, 400)

    def test_conferencia_edicao_preserva_regras_personalizadas(self):
        entrada = self.entrada(tolerancia_impureza_percentual="2", tolerancia_defeitos_percentual="2")
        previa = self.conferir(excluir_id=entrada["id"], peso_total_kg="2500")
        self.assertEqual(previa.status_code, 200, previa.data)
        resposta = self.client.patch(reverse("terceiros-entrada-detalhe", args=(entrada["id"],)), {**self.dados, "peso_total_kg": "2500", "versao": entrada["versao"], "motivo": "Corrigir pesagem"}, format="json", HTTP_IDEMPOTENCY_KEY=str(uuid4()))
        self.assertEqual(resposta.status_code, 200, resposta.data)
        self.assertEqual(Decimal(previa.data["peso_liquido_kg"]), Decimal(resposta.data["peso_liquido_kg"]))
        self.assertEqual(Decimal(previa.data["peso_liquido_kg"]), Decimal(2000))

    def test_alerta_minimo_historico_mediana_e_exclusao_da_edicao(self):
        for _ in range(4):
            self.entrada()
        self.assertEqual(self.conferir(peso_total_kg="3000", tara_kg="1000").data["alertas"], [])
        quinta = self.entrada()
        resposta = self.conferir(peso_total_kg="3000", tara_kg="1000")
        self.assertEqual({a["campo"] for a in resposta.data["alertas"]}, {"tara_kg", "peso_bruto_kg"})
        self.assertEqual(resposta.data["alertas"][0]["amostras"], 5)
        self.assertEqual(self.conferir(peso_total_kg="3000", tara_kg="1000", excluir_id=quinta["id"]).data["alertas"], [])
        self.assertEqual(self.conferir(peso_total_kg="3000", tara_kg="1000", depositante="Outro produtor").data["alertas"], [])
        self.assertEqual(self.conferir(peso_total_kg="3000", tara_kg="1000", placa="DEF1G23").data["alertas"], [])
        self.assertEqual(self.conferir(peso_total_kg="3000", tara_kg="1000", safra="2027").data["alertas"], [])
        self.assertEqual(self.conferir().data["alertas"], [])

    def test_estorno_de_saida_nao_exclui_amostra_mas_entrada_cancelada_sim(self):
        entradas = [self.entrada() for _ in range(5)]
        saida = self.operar("terceiros-saida", entradas[0]["id"], {"quantidade_kg": "100", "data_movimento": "2026-10-07", "destino": "Retirada"})
        movimento = next(m for m in saida["movimentos"] if m["tipo"] == "saida")
        self.operar("terceiros-estorno", movimento["id"], {"motivo": "Desfazer retirada", "data_movimento": "2026-10-07"})
        self.assertEqual(len(self.conferir(peso_total_kg="3000", tara_kg="1000").data["alertas"]), 2)
        movimento = next(m for m in entradas[1]["movimentos"] if m["tipo"] == "entrada")
        self.operar("terceiros-estorno", movimento["id"], {"motivo": "Desfazer entrada", "data_movimento": "2026-10-07"})
        self.assertEqual(self.conferir(peso_total_kg="3000", tara_kg="1000").data["alertas"], [])

    def test_alerta_tambem_compara_cargas_proprias_ativas(self):
        for _ in range(5):
            registrar_carga_colhida(usuario=self.usuario, **{**self.dados_carga(), "peso_total_kg": "1500", "tara_kg": "500", "chave_registro": str(uuid4())})
        resposta = self.conferir(origem="propria", propriedade=self.propriedade.pk, safra=self.grupo.safra, peso_total_kg="3000", tara_kg="1000")
        self.assertEqual(resposta.status_code, 200, resposta.data)
        self.assertEqual(len(resposta.data["alertas"]), 2)
        self.assertEqual(CargaColhida.objects.count(), 5)

    def test_resumo_reflete_edicao_saida_estorno_transferencia_e_cancelamento(self):
        primeira = self.entrada()
        editada = self.client.patch(reverse("terceiros-entrada-detalhe", args=(primeira["id"],)), {**self.dados, "peso_total_kg": "2500", "versao": primeira["versao"], "motivo": "Corrigir peso"}, format="json", HTTP_IDEMPOTENCY_KEY=str(uuid4()))
        self.assertEqual(editada.status_code, 200, editada.data)
        saida = self.operar("terceiros-saida", primeira["id"], {"quantidade_kg": "100", "data_movimento": "2026-10-07", "destino": "Retirada"})
        retirada = next(m for m in saida["movimentos"] if m["tipo"] == "saida")
        estornada = self.operar("terceiros-estorno", retirada["id"], {"motivo": "Desfazer retirada", "data_movimento": "2026-10-07"})
        self.operar("terceiros-transferencia", primeira["id"], {"quantidade_kg": "200", "data_movimento": "2026-10-07", "propriedade": self.propriedade.pk, "cad_pro": str(self.cad_pro.pk), "versao": estornada["versao"]})
        cancelada = self.entrada()
        movimento = next(m for m in cancelada["movimentos"] if m["tipo"] == "entrada")
        self.operar("terceiros-estorno", movimento["id"], {"motivo": "Desfazer entrada", "data_movimento": "2026-10-07"})
        self.entrada(depositante="Outro", safra="2027")
        resumo = self.client.get(reverse("terceiros-resumo"), {"depositante": "Produtor externo", "cultura": "soja", "safra": "2026"})
        self.assertEqual(resumo.status_code, 200, resumo.data)
        self.assertEqual(len(resumo.data["itens"]), 2)
        item = next(i for i in resumo.data['itens'] if i['recebimentos'])
        self.assertEqual((item["recebimentos"], item["cancelados"]), (1, 0))
        self.assertEqual(sum(i['cancelados'] for i in resumo.data['itens']),1)
        self.assertEqual([Decimal(item[c]) for c in ("entradas_kg", "saidas_kg", "transferencias_kg", "saldo_kg")], [Decimal(1960), Decimal(200), Decimal(200), Decimal(1760)])
        self.assertEqual(Decimal(resumo.data["totais"]["saldo_kg"]), Decimal(1760))
        self.assertEqual(self.client.get(reverse("terceiros-resumo"), {"depositante": "Ausente"}).data["itens"], [])

    def test_excel_filtrado_tem_numeros_e_nao_executa_formulas(self):
        self.entrada(depositante="=1+1")
        self.entrada(depositante="Outro", safra="2027")
        resposta = self.client.get(reverse("terceiros-resumo-excel"), {"depositante": "=1+1", "safra": "2026"})
        self.assertEqual(resposta.status_code, 200)
        folha = load_workbook(BytesIO(resposta.content)).active
        self.assertEqual(folha["A8"].value, "=1+1")
        self.assertEqual(folha["A8"].data_type, "s")
        self.assertEqual(folha["F8"].value, 980)
        self.assertEqual(folha["I9"].value, 980)
        self.assertNotIn("Outro", [c.value for linha in folha for c in linha])
        self.assertFalse(any(c.data_type == "f" for linha in folha for c in linha))

    def test_resumo_e_previa_exigem_consulta_exportacao_exige_impressao(self):
        acesso = AcessoUsuario.objects.create(usuario=self.usuario, modulos=["cargas"], permissoes={"cargas": ["consultar"]})
        # Autenticação real inclui a autorização central para a prévia POST.
        self.client.force_authenticate(None)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(self.usuario).access_token}")
        self.assertEqual(self.conferir().status_code, 200)
        self.assertEqual(self.client.get(reverse("terceiros-resumo")).status_code, 200)
        self.assertEqual(self.client.get(reverse("terceiros-resumo-excel")).status_code, 403)
        acesso.permissoes = {"cargas": ["cadastrar"]}
        acesso.save()
        self.assertEqual(self.conferir().status_code, 403)
        self.assertEqual(self.client.get(reverse("terceiros-resumo")).status_code, 403)


class RetificacaoPesagemTests(CargaColhidaBase, APITestCase):
    def setUp(self):
        self.criar_contexto()
        self.client.force_authenticate(self.usuario)
        self.carga = registrar_carga_colhida(usuario=self.usuario, **{**self.dados_carga(), "peso_total_kg": "1500", "tara_kg": "500"})
        self.url = reverse("cargas-colhidas-detail", args=(self.carga.pk,))

    def test_retificacao_total_tara_preserva_original_e_recalcula_ledger(self):
        resposta = self.client.patch(self.url, {"peso_total_kg": "2500", "tara_kg": "500", "peso_bruto_kg": "9999", "motivo_correcao": "Conferência da balança"}, format="json")
        self.assertEqual(resposta.status_code, 200, resposta.data)
        nova = CargaColhida.objects.get(pk=resposta.data["id"])
        self.carga.refresh_from_db()
        self.assertEqual(self.carga.status, CargaColhida.Status.SUBSTITUIDA)
        self.assertEqual(self.carga.substituida_por_id, nova.pk)
        self.assertEqual(self.carga.peso_total_kg, Decimal(1500))
        self.assertEqual(self.carga.tara_kg, Decimal(500))
        self.assertEqual(self.carga.peso_bruto_kg, Decimal(1000))
        self.assertEqual(nova.peso_bruto_kg, Decimal(2000))
        self.assertEqual(nova.peso_liquido_kg, Decimal(1950))
        self.assertEqual(self.carga.motivo_cancelamento, "Conferência da balança")
        self.assertEqual(MovimentacaoGraos.objects.count(), 3)
        self.assertEqual(PosicaoSaldoGraos.objects.get(cad_pro=self.cad_pro).saldo_fisico_kg, Decimal(1950))
        self.assertEqual(CargaColhida.objects.filter(status="ativa").aggregate(total=Sum("peso_liquido_kg"))["total"], Decimal(1950))
        self.assertEqual(self.client.patch(self.url, {"peso_total_kg": "3000"}, format="json").status_code, 400)
        self.assertEqual(MovimentacaoGraos.objects.count(), 3)

    def test_correcao_sem_saldo_livre_nao_estorna_nem_altera_original(self):
        reservar_saldo(usuario=self.usuario, lote=self.carga.lote, quantidade_kg="1", chave_idempotencia="reserva-conferencia")
        antes = (MovimentacaoGraos.objects.count(), CargaColhida.objects.count())
        saldo = PosicaoSaldoGraos.objects.get(cad_pro=self.cad_pro).saldo_fisico_kg
        resposta = self.client.patch(self.url, {"peso_total_kg": "2500", "tara_kg": "500", "motivo_correcao": "Tentar retificar"}, format="json")
        self.assertEqual(resposta.status_code, 409, resposta.data)
        self.carga.refresh_from_db()
        self.assertEqual(self.carga.status, CargaColhida.Status.ATIVA)
        self.assertEqual(self.carga.peso_total_kg, Decimal(1500))
        self.assertEqual((MovimentacaoGraos.objects.count(), CargaColhida.objects.count()), antes)
        posicao = PosicaoSaldoGraos.objects.get(cad_pro=self.cad_pro)
        self.assertEqual((posicao.saldo_fisico_kg, posicao.saldo_comprometido_kg), (saldo, Decimal(1)))

    def test_pesagem_invalida_reverte_todo_o_estorno(self):
        resposta = self.client.patch(self.url, {"peso_total_kg": "400", "tara_kg": "500", "motivo_correcao": "Pesagem inválida"}, format="json")
        self.assertEqual(resposta.status_code, 400, resposta.data)
        self.carga.refresh_from_db()
        self.assertEqual(self.carga.status, CargaColhida.Status.ATIVA)
        self.assertEqual(MovimentacaoGraos.objects.count(), 1)
        self.assertEqual(CargaColhida.objects.count(), 1)

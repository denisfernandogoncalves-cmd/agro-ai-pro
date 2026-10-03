from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

from django.db import close_old_connections, connection
from django.test import TransactionTestCase
from rest_framework.test import APITestCase, APIClient

from apps.cadpro.models import CADProPropriedade
from apps.graos.models import MovimentacaoGraos, PosicaoSaldoGraos
from apps.graos.services import creditar_producao
from apps.propriedades.models import Propriedade
from .models import RateioVendaParticular, VendaGraos
from .posicoes_services import resolver_posicao_inicial
from .tests import ContextoVendaMixin


class ParticularMixin(ContextoVendaMixin):
    url = "/api/comercial/vendas/registrar-saida/"
    previa_url = "/api/comercial/vendas/previa-particular/"

    def preparar(self):
        self.criar_contexto()
        self.propriedade.area_hectares = Decimal("60")
        self.propriedade.save(update_fields=("area_hectares",))
        self.outra = Propriedade.objects.create(nome="Outra produtora", municipio="Sorriso", uf="MT", area_hectares="40")
        CADProPropriedade.objects.create(cad_pro=self.cadpro, propriedade=self.outra)
        self.contexto = {"cultura": "Soja", "safra": "2026/2027", "classificacao_codigo": "TIPO-1", "armazem": self.armazem.pk}
        self.posicoes_particular = []
        for propriedade, saldo in ((self.propriedade, "100"), (self.outra, "900")):
            posicao = resolver_posicao_inicial({**self.contexto, "armazem": self.armazem, "propriedade": propriedade, "cad_pro": self.cadpro})
            lote = propriedade.lotes_graos.get(cad_pro=self.cadpro, safra=self.contexto["safra"])
            creditar_producao(usuario=self.usuario, lote=lote, quantidade_kg=saldo, chave_idempotencia=f"particular-credito-{propriedade.pk}")
            self.posicoes_particular.append(posicao)
        self.client = APIClient()
        self.client.force_authenticate(self.usuario)
        self.dados = {"destino": " particular ", "contexto_particular": self.contexto,
                      "quantidade_kg": "50.000", "data_contrato": "2026-10-01", "placa": "ABC1D23"}
        resposta = self.client.post(self.previa_url, self.dados, format="json")
        assert resposta.status_code == 200, resposta.data
        self.dados["hash_previa"] = resposta.data["hash_previa"]

    def enviar(self, dados=None, chave="particular"):
        return self.client.post(self.url, dados or self.dados, format="json", HTTP_IDEMPOTENCY_KEY=chave)


class ParticularTests(ParticularMixin, APITestCase):
    def setUp(self):
        self.preparar()

    def test_previa_mostra_saldos_antes_e_depois_sem_baixa(self):
        movimentos=MovimentacaoGraos.objects.count()
        previa=self.client.post(self.previa_url,self.dados,format="json")
        self.assertEqual(previa.status_code,200,previa.data)
        self.assertEqual([Decimal(p["saldo_anterior_kg"]) for p in previa.data["parcelas"]],[Decimal("100"),Decimal("900")])
        self.assertEqual([Decimal(p["saldo_posterior_kg"]) for p in previa.data["parcelas"]],[Decimal("70"),Decimal("880")])
        self.assertEqual(MovimentacaoGraos.objects.count(),movimentos)

    def test_mudanca_de_saldo_invalida_previa_sem_registrar_vendas(self):
        lote=self.propriedade.lotes_graos.get(cad_pro=self.cadpro,safra=self.contexto["safra"])
        creditar_producao(usuario=self.usuario,lote=lote,quantidade_kg="1",chave_idempotencia="saldo-mudou")
        resposta=self.enviar()
        self.assertEqual(resposta.status_code,409,resposta.data)
        self.assertEqual(VendaGraos.objects.count(),0)
        self.assertEqual(RateioVendaParticular.objects.count(),0)

    def test_desconta_pela_area_em_todas_as_propriedades_e_nao_pelo_saldo(self):
        resposta = self.enviar()
        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.assertEqual(VendaGraos.objects.count(), 2)
        snapshot = resposta.data["rateio_particular_snapshot"]
        self.assertEqual([p["quantidade_kg"] for p in snapshot["parcelas"]], ["30.000", "20.000"])
        self.assertEqual(snapshot["quantidade_total_kg"], "50.000")
        for posicao, saldo in zip(self.posicoes_particular, ("70", "880")):
            posicao.refresh_from_db()
            self.assertEqual(posicao.saldo_fisico_kg, Decimal(saldo))
            self.assertEqual(posicao.saldo_comprometido_kg, Decimal("0"))
        self.posicao.refresh_from_db()
        self.assertEqual(self.posicao.saldo_fisico_kg, Decimal("1000"))
        self.assertTrue(all(v.status == "entregue" for v in VendaGraos.objects.all()))

    def test_reenvio_preserva_snapshot_mesmo_apos_alteracao_de_area(self):
        primeira = self.enviar()
        self.assertEqual(primeira.status_code, 201, primeira.data)
        movimentos = MovimentacaoGraos.objects.count()
        self.propriedade.area_hectares = Decimal("1")
        self.propriedade.save(update_fields=("area_hectares",))
        segunda = self.enviar()
        self.assertEqual(segunda.status_code, 201, segunda.data)
        self.assertEqual(primeira.data, segunda.data)
        self.assertEqual(MovimentacaoGraos.objects.count(), movimentos)
        self.assertEqual(RateioVendaParticular.objects.count(), 1)
        self.assertEqual(self.enviar({**self.dados, "motorista": "Outro"}).status_code, 409)

    def test_previa_nao_movimenta_e_arredondamento_soma_exatamente_um_grama(self):
        movimentos = MovimentacaoGraos.objects.count()
        for peso in ("0.001", "0.003", "50.123"):
            resposta = self.client.post(self.previa_url, {**self.dados, "quantidade_kg": peso}, format="json")
            self.assertEqual(resposta.status_code, 200, resposta.data)
            pesos = [Decimal(p["quantidade_kg"]) for p in resposta.data["parcelas"]]
            self.assertEqual(sum(pesos), Decimal(peso))
            self.assertTrue(all(p >= 0 for p in pesos))
        self.assertEqual(MovimentacaoGraos.objects.count(), movimentos)
        self.assertEqual(RateioVendaParticular.objects.count(), 0)

    def test_sem_estoque_anterior_cria_posicoes_negativas_sem_credito_ficticio(self):
        contexto = {**self.contexto, "safra": "2030"}
        previa = self.client.post(self.previa_url, {**self.dados, "contexto_particular": contexto}, format="json").data
        resposta = self.enviar({**self.dados, "contexto_particular": contexto, "hash_previa": previa["hash_previa"]})
        self.assertEqual(resposta.status_code, 201, resposta.data)
        saldos = list(PosicaoSaldoGraos.objects.filter(safra="2030").order_by("propriedade_id").values_list("saldo_fisico_kg", flat=True))
        self.assertEqual(saldos, [Decimal("-30"), Decimal("-20")])

    def test_falha_em_uma_parcela_reverte_todas_as_saidas(self):
        from unittest.mock import patch
        from .services import VendaGraosError, registrar_venda_com_saida
        antes = MovimentacaoGraos.objects.count()
        contador = 0

        def registrar(**kwargs):
            nonlocal contador
            contador += 1
            if contador == 2:
                raise VendaGraosError("Falha na segunda propriedade")
            return registrar_venda_com_saida(**kwargs)

        with patch("apps.vendas.particular_services.registrar_venda_com_saida", side_effect=registrar):
            resposta = self.enviar()
        self.assertEqual(resposta.status_code, 400, resposta.data)
        self.assertEqual(MovimentacaoGraos.objects.count(), antes)
        self.assertEqual(VendaGraos.objects.count(), 0)
        self.assertEqual(RateioVendaParticular.objects.count(), 0)

    def test_area_alterada_exige_nova_previa_sem_baixa_parcial(self):
        self.propriedade.area_hectares = Decimal("61")
        self.propriedade.save(update_fields=("area_hectares",))
        self.assertEqual(self.enviar().status_code, 409)
        self.assertEqual(VendaGraos.objects.count(), 0)
        self.assertEqual(RateioVendaParticular.objects.count(), 0)

    def test_destino_comum_nao_aceita_rateio_e_particular_nao_aceita_posicao_individual(self):
        for dados in ({**self.dados, "destino": "Cooperativa"}, {**self.dados, "posicao": self.posicao.pk},
                      {k: v for k, v in self.dados.items() if k != "hash_previa"}):
            self.assertEqual(self.enviar(dados).status_code, 400)
        self.assertEqual(VendaGraos.objects.count(), 0)

    def test_vinculo_ambiguo_nao_ignora_propriedade(self):
        CADProPropriedade.objects.filter(propriedade=self.outra).update(ativo=False)
        resposta = self.client.post(self.previa_url, self.dados, format="json")
        self.assertEqual(resposta.status_code, 400)
        self.assertIn(self.outra.nome, str(resposta.data))
        self.assertEqual(self.enviar().status_code, 400)
        self.assertEqual(VendaGraos.objects.count(), 0)

    def test_autenticacao_e_chave_obrigatorias(self):
        self.assertEqual(self.client.post(self.url, self.dados, format="json").status_code, 400)
        self.client.force_authenticate(None)
        self.assertEqual(self.enviar().status_code, 401)
        self.assertEqual(self.client.post(self.previa_url, self.dados, format="json").status_code, 401)


class ParticularConcorrenciaTests(ParticularMixin, TransactionTestCase):
    def test_reenvios_simultaneos_baixam_uma_unica_vez(self):
        if connection.vendor != "postgresql":
            self.skipTest("Requer bloqueios reais do PostgreSQL.")
        self.preparar()
        barreira = Barrier(2)

        def enviar(_):
            close_old_connections()
            try:
                client = APIClient()
                client.force_authenticate(self.usuario)
                barreira.wait(timeout=10)
                return client.post(self.url, self.dados, format="json", HTTP_IDEMPOTENCY_KEY="simultanea").status_code
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            self.assertEqual(list(executor.map(enviar, range(2))), [201, 201])
        self.assertEqual(VendaGraos.objects.count(), 2)
        self.assertEqual(RateioVendaParticular.objects.count(), 1)
        for posicao, saldo in zip(self.posicoes_particular, ("70", "880")):
            posicao.refresh_from_db()
            self.assertEqual(posicao.saldo_fisico_kg, Decimal(saldo))

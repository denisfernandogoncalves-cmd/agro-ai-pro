from decimal import Decimal

from rest_framework.test import APITestCase

from apps.cadpro.models import CADPro, CADProPropriedade
from apps.propriedades.models import Propriedade
from .models import LoteGraos, MovimentacaoGraos, PosicaoSaldoGraos
from .services import reservar_saldo
from .tests import GraosSaldoBase


class TransferenciaCADProInterfaceTests(GraosSaldoBase, APITestCase):
    def setUp(self):
        self.criar_contexto()
        self.client.force_authenticate(self.usuario)
        self.destinatario = CADPro.objects.create(codigo="CAD-DESTINO", descricao="Destinatário")
        CADProPropriedade.objects.create(cad_pro=self.destinatario, propriedade=self.propriedade)
        self.destino = LoteGraos.objects.create(codigo="DESTINO", cad_pro=self.destinatario,
            propriedade=self.propriedade, armazem=self.armazem, cultura=self.lote.cultura,
            safra=self.lote.safra, classificacao_codigo=self.lote.classificacao_codigo)
        self.creditar("1000")
        reservar_saldo(usuario=self.usuario, lote=self.lote, quantidade_kg="100", chave_idempotencia="reserva")

    def transferir(self, quantidade="300", chave="transferencia"):
        origem = PosicaoSaldoGraos.objects.get(
            propriedade=self.lote.propriedade,
            cad_pro=self.lote.cad_pro,
            cultura=self.lote.cultura,
            safra=self.lote.safra,
            classificacao_codigo=self.lote.classificacao_codigo,
            armazem=self.lote.armazem,
        )
        destino = PosicaoSaldoGraos.objects.get_or_create(
            propriedade=self.destino.propriedade,
            cad_pro=self.destino.cad_pro,
            cultura=self.destino.cultura,
            safra=self.destino.safra,
            classificacao_codigo=self.destino.classificacao_codigo,
            armazem=self.destino.armazem,
        )[0]
        return self.client.post("/api/graos/saldos/transferir/", {
            "posicao_origem": origem.pk, "posicao_destino": destino.pk,
            "quantidade_kg": quantidade, "data_movimento": "2026-08-30",
            "chave_idempotencia": chave, "referencia_externa": "Documento 123",
        }, format="json")

    def test_transfere_entre_cadpros_preservando_producao_reserva_e_total(self):
        for status_esperado in (201, 200):
            resposta = self.transferir()
            self.assertEqual(resposta.status_code, status_esperado, resposta.data)
        origem = PosicaoSaldoGraos.objects.get(cad_pro=self.cad_pro)
        destino = PosicaoSaldoGraos.objects.get(cad_pro=self.destinatario)
        self.assertEqual(origem.saldo_fisico_kg, Decimal("700"))
        self.assertEqual(origem.saldo_comprometido_kg, Decimal("100"))
        self.assertEqual(destino.saldo_fisico_kg, Decimal("300"))
        self.assertEqual(destino.propriedade_id, self.propriedade.pk)
        self.assertEqual(MovimentacaoGraos.objects.filter(operacao__startswith="transferencia_").count(), 2)

    def test_nao_transfere_saldo_reservado(self):
        resposta = self.transferir("901")
        self.assertEqual(resposta.status_code, 409, resposta.data)
        self.assertEqual(PosicaoSaldoGraos.objects.get(cad_pro=self.cad_pro).saldo_fisico_kg, Decimal("1000"))
        self.assertFalse(MovimentacaoGraos.objects.filter(operacao__startswith="transferencia_").exists())

    def test_transfere_entre_propriedades_com_cadpro_igual_ou_diferente(self):
        outra = Propriedade.objects.create(nome="Outra produtora", municipio="Teste", area_hectares="10")
        CADProPropriedade.objects.create(cad_pro=self.destinatario, propriedade=outra)
        CADProPropriedade.objects.create(cad_pro=self.cad_pro, propriedade=outra)
        self.destino.propriedade = outra
        self.destino.save()
        resposta = self.transferir()
        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.destino = LoteGraos.objects.create(codigo="MESMO-CAD", cad_pro=self.cad_pro,
            propriedade=outra, armazem=self.armazem, cultura=self.lote.cultura,
            safra=self.lote.safra, classificacao_codigo=self.lote.classificacao_codigo)
        resposta = self.transferir(chave="mesmo-cad")
        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.assertEqual(PosicaoSaldoGraos.objects.get(cad_pro=self.cad_pro, propriedade=self.propriedade).saldo_fisico_kg, Decimal("400"))
        self.assertEqual(PosicaoSaldoGraos.objects.get(cad_pro=self.cad_pro, propriedade=outra).saldo_fisico_kg, Decimal("300"))
        self.assertEqual(sum(p.saldo_fisico_kg for p in PosicaoSaldoGraos.objects.all()), Decimal("1000"))

    def test_bloqueia_mesma_posicao_mesmo_com_outro_lote(self):
        self.destino.cad_pro = self.cad_pro
        self.destino.save()
        resposta = self.transferir()
        self.assertEqual(resposta.status_code, 400, resposta.data)
        self.assertIn("posições", str(resposta.data))
        self.assertFalse(MovimentacaoGraos.objects.filter(operacao__startswith="transferencia_").exists())

    def test_posicoes_substituem_lotes_no_contrato_da_interface(self):
        resposta = self.transferir("25", chave="sem-lotes")
        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.assertEqual(resposta.data["codigo"], "saldo_transferido")
        self.assertEqual(len(resposta.data["movimentacoes"]), 2)

    def test_exige_as_duas_posicoes(self):
        origem = PosicaoSaldoGraos.objects.get(cad_pro=self.cad_pro)
        resposta = self.client.post("/api/graos/saldos/transferir/", {
            "posicao_origem": origem.pk,
            "quantidade_kg": "10",
            "chave_idempotencia": "posicao-incompleta",
        }, format="json")
        self.assertEqual(resposta.status_code, 400, resposta.data)
        self.assertIn("posição oficial de destino", str(resposta.data))


class TransferenciaSemColheitaTests(TransferenciaCADProInterfaceTests):
    def setUp(self):
        super().setUp()
        self.nova_propriedade = Propriedade.objects.create(nome="Sem colheita", municipio="Teste", area_hectares="10")
        self.vinculo = CADProPropriedade.objects.create(cad_pro=self.destinatario, propriedade=self.nova_propriedade)
        self.payload = {
            "posicao_origem": PosicaoSaldoGraos.objects.get(cad_pro=self.cad_pro).pk,
            "propriedade_destino": self.nova_propriedade.pk,
            "cad_pro_destino": str(self.destinatario.pk),
            "quantidade_kg": "300", "chave_idempotencia": "sem-colheita",
            "data_movimento": "2026-09-30",
        }

    def enviar_cadastro(self, **alteracoes):
        return self.client.post("/api/graos/saldos/transferir/", {**self.payload, **alteracoes}, format="json")

    def test_cria_destino_sem_colheita_e_reenvio_nao_duplica(self):
        self.assertFalse(LoteGraos.objects.filter(propriedade=self.nova_propriedade).exists())
        for esperado in (201, 200):
            resposta = self.enviar_cadastro()
            self.assertEqual(resposta.status_code, esperado, resposta.data)
        destino = PosicaoSaldoGraos.objects.get(propriedade=self.nova_propriedade)
        self.assertEqual(destino.saldo_fisico_kg, Decimal("300"))
        self.assertEqual(destino.saldo_comprometido_kg, Decimal("0"))
        self.assertEqual((destino.cultura, destino.safra, destino.classificacao_codigo, destino.armazem_id),
                         (self.lote.cultura, self.lote.safra, self.lote.classificacao_codigo, self.lote.armazem_id))
        self.assertEqual(LoteGraos.objects.filter(propriedade=self.nova_propriedade).count(), 1)
        movimentos = MovimentacaoGraos.objects.filter(operacao__startswith="transferencia_")
        self.assertEqual(movimentos.count(), 2)
        self.assertEqual(movimentos.values("origem_id").distinct().count(), 1)
        self.assertFalse(MovimentacaoGraos.objects.filter(lote__propriedade=self.nova_propriedade, operacao="credito_producao").exists())
        self.assertEqual(sum(p.saldo_fisico_kg for p in PosicaoSaldoGraos.objects.all()), Decimal("1000"))
        resposta = self.enviar_cadastro(chave_idempotencia="segunda")
        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.assertEqual(LoteGraos.objects.filter(propriedade=self.nova_propriedade).count(), 1)

    def test_saldo_insuficiente_reverte_criacao_destino(self):
        resposta = self.enviar_cadastro(quantidade_kg="901")
        self.assertEqual(resposta.status_code, 409, resposta.data)
        self.assertFalse(LoteGraos.objects.filter(propriedade=self.nova_propriedade).exists())
        self.assertFalse(PosicaoSaldoGraos.objects.filter(propriedade=self.nova_propriedade).exists())
        self.assertFalse(MovimentacaoGraos.objects.filter(operacao__startswith="transferencia_").exists())

    def test_rejeita_vinculo_inativo(self):
        self.vinculo.ativo = False
        self.vinculo.save()
        resposta = self.enviar_cadastro()
        self.assertEqual(resposta.status_code, 409, resposta.data)
        self.assertFalse(LoteGraos.objects.filter(propriedade=self.nova_propriedade).exists())

    def test_rejeita_cadpro_inativo(self):
        self.destinatario.ativo = False
        self.destinatario.save()
        resposta = self.enviar_cadastro()
        self.assertEqual(resposta.status_code, 409, resposta.data)

    def test_rejeita_mesmo_destino_e_chave_com_conteudo_diferente(self):
        resposta = self.enviar_cadastro(propriedade_destino=self.propriedade.pk, cad_pro_destino=str(self.cad_pro.pk))
        self.assertEqual(resposta.status_code, 409, resposta.data)
        self.assertEqual(self.enviar_cadastro().status_code, 201)
        resposta = self.enviar_cadastro(quantidade_kg="301")
        self.assertEqual(resposta.status_code, 409, resposta.data)

    def test_rejeita_destinos_ambiguos(self):
        resposta = self.enviar_cadastro(posicao_destino=self.payload["posicao_origem"])
        self.assertEqual(resposta.status_code, 400, resposta.data)

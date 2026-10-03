from decimal import Decimal
from django.core.exceptions import ValidationError
from rest_framework.test import APITestCase
from apps.accounts.models import AcessoUsuario
from apps.cadpro.models import CADPro, CADProPropriedade
from .models import LoteGraos, MovimentacaoGraos, PosicaoSaldoGraos, CorrecaoTransferenciaSaldo
from .services import transferir_saldo_fisico, reservar_saldo
from .tests import GraosSaldoBase
from .test_cargas_colhidas import CargaColhidaBase
from .cargas_services import registrar_carga_colhida


class CorrecaoTransferenciaTests(GraosSaldoBase, APITestCase):
    def setUp(self):
        self.criar_contexto(); self.client.force_authenticate(self.usuario); self.creditar()
        self.cad_destino = CADPro.objects.create(codigo="DESTINO", descricao="Destinatário")
        CADProPropriedade.objects.create(cad_pro=self.cad_destino, propriedade=self.propriedade)
        self.destino = LoteGraos.objects.create(codigo="DESTINO", cad_pro=self.cad_destino, propriedade=self.propriedade, armazem=self.armazem, cultura=self.lote.cultura, safra=self.lote.safra, classificacao_codigo=self.lote.classificacao_codigo)
        resultado = transferir_saldo_fisico(usuario=self.usuario,lote_origem=self.lote,lote_destino=self.destino,quantidade_kg="300",chave_idempotencia="original")
        self.saida = MovimentacaoGraos.objects.get(pk=resultado.movimentacoes[0].id,operacao="transferencia_saida")
        self.origem_pos = PosicaoSaldoGraos.objects.get(cad_pro=self.cad_pro)
        self.destino_pos = PosicaoSaldoGraos.objects.get(cad_pro=self.cad_destino)
        self.url = f"/api/graos/transferencias/{self.saida.pk}/"
        self.payload = {"motivo":"Corrigir documento", "chave_idempotencia":"correcao", "posicao_origem":self.origem_pos.pk,"posicao_destino":self.destino_pos.pk,"quantidade_kg":"250","data_movimento":"2026-10-02","referencia_externa":"CORRIGIDO"}

    def saldos(self):
        return list(PosicaoSaldoGraos.objects.order_by("id").values_list("saldo_fisico_kg",flat=True))

    def test_edicao_atomica_original_preservado_e_reenvio(self):
        for repeticao in (False,True):
            resposta=self.client.patch(self.url,self.payload,format="json")
            self.assertEqual(resposta.status_code,200,resposta.data); self.assertEqual(resposta.data["idempotente"],repeticao)
        self.assertEqual(self.saldos(),[Decimal("750"),Decimal("250")])
        self.assertEqual(MovimentacaoGraos.objects.filter(estorno_de__origem=self.saida.origem).count(),2)
        self.assertEqual(MovimentacaoGraos.objects.filter(operacao__startswith="transferencia_").count(),4)
        self.saida.refresh_from_db(); self.assertEqual(self.saida.quantidade_kg,Decimal("300"))
        self.assertEqual(CorrecaoTransferenciaSaldo.objects.count(),1)
        serializada=self.client.get("/api/graos/movimentacoes/")
        self.assertEqual(serializada.status_code,200,serializada.data)
        valores=serializada.data if isinstance(serializada.data,list) else serializada.data["results"]
        original=next(x for x in valores if x["id"]==self.saida.pk)
        self.assertTrue(original["estornado"]); self.assertEqual(original["correcao_transferencia"]["acao"],"editar")

    def test_exclusao_retoma_saldo_e_reenvio(self):
        for repeticao in (False,True):
            resposta=self.client.delete(self.url,{"motivo":"Cancelar transferência","chave_idempotencia":"excluir"},format="json")
            self.assertEqual(resposta.status_code,200,resposta.data); self.assertEqual(resposta.data["idempotente"],repeticao)
        self.assertEqual(self.saldos(),[Decimal("1000"),Decimal("0")])
        self.assertEqual(MovimentacaoGraos.objects.filter(estorno_de__origem=self.saida.origem).count(),2)

    def test_mesma_chave_dados_diferentes_e_original_encerrado(self):
        self.assertEqual(self.client.patch(self.url,self.payload,format="json").status_code,200)
        self.assertEqual(self.client.patch(self.url,{**self.payload,"quantidade_kg":"251"},format="json").status_code,409)
        self.assertEqual(self.client.delete(self.url,{"motivo":"Outra correção","chave_idempotencia":"segunda"},format="json").status_code,409)
        self.assertEqual(self.saldos(),[Decimal("750"),Decimal("250")])

    def test_exclusao_bloqueada_por_reserva_sem_estorno_parcial(self):
        reservar_saldo(usuario=self.usuario,lote=self.destino,quantidade_kg="200",chave_idempotencia="reserva")
        quantidade=MovimentacaoGraos.objects.count()
        resposta=self.client.delete(self.url,{"motivo":"Cancelar","chave_idempotencia":"excluir"},format="json")
        self.assertEqual(resposta.status_code,409,resposta.data); self.assertEqual(self.saldos(),[Decimal("700"),Decimal("300")])
        self.assertEqual(MovimentacaoGraos.objects.count(),quantidade); self.assertFalse(CorrecaoTransferenciaSaldo.objects.exists())

    def test_edicao_preserva_reserva_com_negativo_apenas_transitorio(self):
        reservar_saldo(usuario=self.usuario,lote=self.destino,quantidade_kg="200",chave_idempotencia="reserva")
        resposta=self.client.patch(self.url,self.payload,format="json")
        self.assertEqual(resposta.status_code,200,resposta.data); self.assertEqual(self.saldos(),[Decimal("750"),Decimal("250")])
        self.destino_pos.refresh_from_db(); self.assertEqual(self.destino_pos.saldo_comprometido_kg,Decimal("200"))

    def test_edicao_inviavel_reverte_todas_as_pernas(self):
        reservar_saldo(usuario=self.usuario,lote=self.destino,quantidade_kg="200",chave_idempotencia="reserva")
        quantidade=MovimentacaoGraos.objects.count()
        resposta=self.client.patch(self.url,{**self.payload,"quantidade_kg":"100"},format="json")
        self.assertEqual(resposta.status_code,409,resposta.data); self.assertEqual(self.saldos(),[Decimal("700"),Decimal("300")])
        self.assertEqual(MovimentacaoGraos.objects.count(),quantidade); self.assertFalse(CorrecaoTransferenciaSaldo.objects.exists())

    def test_motivo_obrigatorio_e_permissoes_independentes(self):
        self.assertEqual(self.client.patch(self.url,{**self.payload,"motivo":" "},format="json").status_code,400)
        acesso=AcessoUsuario.objects.create(usuario=self.usuario,modulos=["transferencias"],permissoes={"transferencias":["consultar","editar"]})
        self.assertEqual(self.client.delete(self.url,{"motivo":"Cancelar","chave_idempotencia":"excluir"},format="json").status_code,403)
        resposta=self.client.patch(self.url,self.payload,format="json");self.assertEqual(resposta.status_code,200,resposta.data)
        acesso.permissoes={"transferencias":["consultar"]};acesso.save()
        self.assertEqual(self.client.patch(self.url,self.payload,format="json").status_code,403)

    def test_estorno_legado_e_conferencia_nao_contornam_permissao_transferencia(self):
        AcessoUsuario.objects.create(usuario=self.usuario,modulos=["producao-saldos","transferencias"],permissoes={"producao-saldos":["consultar","excluir"],"transferencias":["consultar"]})
        dados={"movimentacao":self.saida.pk,"observacoes":"Tentativa sem permissão","chave_idempotencia":"bypass"}
        for url in (f"/api/graos/movimentacoes/{self.saida.pk}/estornar/", "/api/graos/saldos/estornar-movimentacao/", f"/api/core/conferencia/movimentos/{self.saida.pk}/estornar/"):
            resposta=self.client.post(url,dados,format="json");self.assertEqual(resposta.status_code,403,(url,resposta.data))
        self.assertEqual(self.saldos(),[Decimal("700"),Decimal("300")])
        self.assertFalse(CorrecaoTransferenciaSaldo.objects.exists())

    def test_permissao_excluir_sem_editar(self):
        AcessoUsuario.objects.create(usuario=self.usuario,modulos=["transferencias"],permissoes={"transferencias":["consultar","excluir"]})
        self.assertEqual(self.client.patch(self.url,self.payload,format="json").status_code,403)
        resposta=self.client.delete(self.url,{"motivo":"Cancelar","chave_idempotencia":"excluir"},format="json");self.assertEqual(resposta.status_code,200,resposta.data)

    def test_cad_inativo_bloqueia_sem_mutar_historico(self):
        self.cad_pro.ativo=False;self.cad_pro.save()
        resposta=self.client.delete(self.url,{"motivo":"Cancelar","chave_idempotencia":"excluir"},format="json")
        self.assertEqual(resposta.status_code,409,resposta.data);self.assertFalse(CorrecaoTransferenciaSaldo.objects.exists())
        self.assertEqual(self.saldos(),[Decimal("700"),Decimal("300")])

    def test_correcao_imutavel(self):
        resposta=self.client.patch(self.url,self.payload,format="json");self.assertEqual(resposta.status_code,200,resposta.data)
        registro=CorrecaoTransferenciaSaldo.objects.get()
        for alterar in (lambda:registro.save(),lambda:registro.delete(),lambda:CorrecaoTransferenciaSaldo.objects.update(motivo="Alterado"),lambda:CorrecaoTransferenciaSaldo.objects.all().delete()):
            with self.assertRaises(ValidationError): alterar()


class CancelarCargaTransferidaTests(CargaColhidaBase,APITestCase):
    def setUp(self):
        self.criar_contexto();self.client.force_authenticate(self.usuario)
        self.carga=registrar_carga_colhida(usuario=self.usuario,**self.dados_carga())
        self.posicao=PosicaoSaldoGraos.objects.get()
        cad=CADPro.objects.create(codigo="OUTRO", descricao="Destinatário");CADProPropriedade.objects.create(cad_pro=cad,propriedade=self.propriedade)
        self.destino=LoteGraos.objects.create(codigo="DESTINO",cad_pro=cad,propriedade=self.propriedade,armazem=self.armazem,cultura=self.posicao.cultura,safra=self.posicao.safra,classificacao_codigo=self.posicao.classificacao_codigo)
        resultado=transferir_saldo_fisico(usuario=self.usuario,lote_origem=self.carga.lote,lote_destino=self.destino,quantidade_kg=self.carga.peso_liquido_kg,chave_idempotencia="transferencia")
        self.saida=next(m for m in resultado.movimentacoes if m.operacao=="transferencia_saida")
        self.url=f"/api/graos/cargas-colhidas/{self.carga.pk}/"

    def test_previa_leitura_bloqueio_transferencia_e_cancelamento_apos_estorno(self):
        quantidade=MovimentacaoGraos.objects.count()
        previa=self.client.get(self.url+"previa-exclusao/")
        self.assertEqual(previa.status_code,200,previa.data);self.assertFalse(previa.data["pode_excluir"])
        self.assertEqual(previa.data["transferencias"][0]["movimento_saida"],int(self.saida.id))
        self.assertEqual(MovimentacaoGraos.objects.count(),quantidade)
        self.assertEqual(self.client.delete(self.url,{"motivo":"Cancelar"},format="json").status_code,409)
        resposta=self.client.delete(f"/api/graos/transferencias/{self.saida.id}/",{"motivo":"Cancelar transferência","chave_idempotencia":"excluir"},format="json")
        self.assertEqual(resposta.status_code,200,resposta.data)
        self.assertTrue(self.client.get(self.url+"previa-exclusao/").data["pode_excluir"])
        self.assertEqual(self.client.delete(self.url,{"motivo":"Cancelar carga"},format="json").status_code,204)
        self.assertEqual(sum(PosicaoSaldoGraos.objects.values_list("saldo_fisico_kg",flat=True)),Decimal("0"))


from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless
from django.db import connection, close_old_connections
from django.test import TransactionTestCase
from .transferencias_correcoes import corrigir_transferencia
from .services import SaldoGraosError


@skipUnless(connection.vendor == "postgresql", "Requer bloqueios reais do PostgreSQL.")
class CorrecaoTransferenciaConcorrenteTests(GraosSaldoBase, TransactionTestCase):
    def setUp(self):
        self.criar_contexto(); self.creditar()
        cad = CADPro.objects.create(codigo="CONCORRENTE", descricao="Destinatário")
        CADProPropriedade.objects.create(cad_pro=cad, propriedade=self.propriedade)
        destino = LoteGraos.objects.create(codigo="DESTINO", cad_pro=cad, propriedade=self.propriedade, armazem=self.armazem, cultura=self.lote.cultura, safra=self.lote.safra, classificacao_codigo=self.lote.classificacao_codigo)
        resultado = transferir_saldo_fisico(usuario=self.usuario, lote_origem=self.lote, lote_destino=destino, quantidade_kg="300", chave_idempotencia="original")
        self.saida_id = next(m.id for m in resultado.movimentacoes if m.operacao == "transferencia_saida")

    def test_exclusoes_concorrentes_nao_duplicam_estorno(self):
        barreira = Barrier(2)
        def excluir(indice):
            close_old_connections()
            try:
                movimento = MovimentacaoGraos.objects.get(pk=self.saida_id)
                barreira.wait(timeout=10)
                try:
                    corrigir_transferencia(usuario=self.usuario, movimento=movimento, acao="excluir", motivo="Correção concorrente", chave=f"concorrente:{indice}")
                    return "ok"
                except SaldoGraosError:
                    return "bloqueado"
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as executor:
            futuros = [executor.submit(excluir, indice) for indice in (1,2)]
            respostas = [f.result(timeout=20) for f in futuros]
        self.assertCountEqual(respostas, ["ok", "bloqueado"])
        self.assertEqual(CorrecaoTransferenciaSaldo.objects.count(), 1)
        self.assertEqual(MovimentacaoGraos.objects.filter(operacao="estorno").count(), 2)
        self.assertEqual(sum(PosicaoSaldoGraos.objects.values_list("saldo_fisico_kg",flat=True)), Decimal("1000"))

from decimal import Decimal
from uuid import uuid4
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework.test import APITestCase
from apps.accounts.models import AcessoUsuario
from apps.core.painel import construir_painel
from apps.relatorios.selectors import selecionar_relatorio_operacional
from .models import EntradaProducaoTerceiro, MovimentoProducaoTerceiro, PosicaoSaldoGraos, MovimentacaoGraos
from .test_cargas_colhidas import CargaColhidaBase
from .cargas_services import registrar_carga_colhida, CargaColhidaError
from .services import saldo_armazem, CapacidadeArmazemExcedidaError
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier
from unittest import skipUnless
from django.db import close_old_connections, connection
from django.test import TransactionTestCase
from rest_framework.exceptions import ValidationError as APIValidationError
from .terceiros import executar_terceiro


class TerceirosTests(CargaColhidaBase, APITestCase):
    def setUp(self):
        self.criar_contexto()
        self.client.force_authenticate(self.usuario)

    def entrada(self, peso="600.000", chave=None):
        return self.client.post("/api/graos/terceiros/entradas/", {"depositante":"Produtor externo", "propriedade_origem":"Sítio de terceiro", "cad_pro":"0009", "cultura":"Milho", "safra":"2026", "armazem":self.armazem.pk, "peso_bruto_kg":peso, "umidade_percentual":"14", "impureza_percentual":"0", "defeitos_percentual":"0", "data_entrada":"2026-10-05"}, format="json", HTTP_IDEMPOTENCY_KEY=chave or str(uuid4()))

    def test_descontos_iguais_cargas_proprias_e_previa_sem_movimento(self):
        from .cargas_services import calcular_peso_liquido
        dados = {"cultura":"Milho", "peso_bruto_kg":"1000", "umidade_percentual":"20.5", "impureza_percentual":"2", "defeitos_percentual":"3", "ph":"70", "ph_minimo":"75", "desconto_ph_por_ponto":"0.1"}
        esperado = calcular_peso_liquido(**dados)
        previa = self.client.post("/api/graos/terceiros/previa/", dados, format="json")
        self.assertEqual(previa.status_code, 200)
        self.assertEqual(Decimal(previa.data["peso_liquido_kg"]), esperado[2])
        self.assertEqual(EntradaProducaoTerceiro.objects.count(), 0)
        resposta = self.client.post("/api/graos/terceiros/entradas/", {**dados, "depositante":"Nome apenas", "safra":"2026", "armazem":self.armazem.pk, "data_entrada":"2026-10-05", "peso_liquido_kg":"99999"}, format="json", HTTP_IDEMPOTENCY_KEY=str(uuid4()))
        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.assertEqual(Decimal(resposta.data["peso_liquido_kg"]), esperado[2])
        self.assertEqual(Decimal(resposta.data["saldo_kg"]), esperado[2])
        self.assertEqual(resposta.data["regra_desconto_aplicada"]["metodo"], esperado[4]["metodo"])
        self.assertEqual(Decimal(resposta.data["desconto_total_kg"]), esperado[1])
        self.assertEqual(resposta.data["propriedade_origem"], "")
        self.assertEqual(resposta.data["cad_pro"], "")
        dados["umidade_percentual"] = "14.1"
        self.assertEqual(self.client.post("/api/graos/terceiros/previa/", dados, format="json").status_code, 400)

    def test_editar_excluir_preserva_historico_e_saldos(self):
        entrada = self.entrada().data
        retirada = self.saida(entrada["id"], "100").data
        url = f"/api/graos/terceiros/entradas/{entrada['id']}/"
        dados = {"depositante":"Nome corrigido", "cultura":"Milho", "safra":"2026", "armazem":self.armazem.pk, "peso_bruto_kg":"700", "umidade_percentual":"14", "impureza_percentual":"0", "defeitos_percentual":"0", "data_entrada":"2026-10-05", "versao":retirada["versao"], "motivo":"Conferência da pesagem"}
        chave = str(uuid4())
        editada = self.client.patch(url, dados, format="json", HTTP_IDEMPOTENCY_KEY=chave)
        self.assertEqual(editada.status_code,200,editada.data)
        self.assertEqual(Decimal(editada.data["saldo_kg"]),Decimal("600"))
        self.assertEqual(Decimal(editada.data["peso_liquido_kg"]),Decimal("700"))
        edicao = MovimentoProducaoTerceiro.objects.get(tipo="edicao")
        self.assertEqual(edicao.snapshot_antes["depositante"],"Produtor externo")
        self.assertEqual(edicao.snapshot_depois["depositante"],"Nome corrigido")
        self.assertEqual(self.client.patch(url,dados,format="json",HTTP_IDEMPOTENCY_KEY=chave).status_code,200)
        self.assertEqual(MovimentoProducaoTerceiro.objects.filter(tipo="edicao").count(),1)
        self.assertEqual(self.client.patch(url,dados,format="json",HTTP_IDEMPOTENCY_KEY=str(uuid4())).status_code,400)
        invalidos={**dados,"versao":editada.data["versao"],"peso_bruto_kg":"50"}
        self.assertEqual(self.client.patch(url,invalidos,format="json",HTTP_IDEMPOTENCY_KEY=str(uuid4())).status_code,400)
        self.assertEqual(self.client.delete(url,{"motivo":"Excluir","data_movimento":"2026-10-05","versao":editada.data["versao"]},format="json",HTTP_IDEMPOTENCY_KEY=str(uuid4())).status_code,400)
        movimento_saida = next(m for m in retirada["movimentos"] if m["tipo"]=="saida")
        restaurada=self.estornar(movimento_saida["id"])
        self.assertEqual(restaurada.status_code,201,restaurada.data)
        excluida=self.client.delete(url,{"motivo":"Entrada incorreta","data_movimento":"2026-10-05","versao":restaurada.data["versao"]},format="json",HTTP_IDEMPOTENCY_KEY=str(uuid4()))
        self.assertEqual(excluida.status_code,200,excluida.data)
        self.assertEqual(Decimal(excluida.data["saldo_kg"]),Decimal("0"))
        self.assertEqual(EntradaProducaoTerceiro.objects.count(),1)
        self.assertEqual(sum(m.delta_kg for m in MovimentoProducaoTerceiro.objects.all()),Decimal("0"))
        self.assertEqual(self.client.patch(url,{**dados,"versao":excluida.data["versao"]},format="json",HTTP_IDEMPOTENCY_KEY=str(uuid4())).status_code,400)

    def test_edicao_metadados_delta_zero_e_permissao(self):
        entrada=self.entrada().data
        url=f"/api/graos/terceiros/entradas/{entrada['id']}/"
        dados={"depositante":"Corrigido", "cultura":"Milho", "safra":"2026", "armazem":self.armazem.pk, "peso_bruto_kg":"600", "umidade_percentual":"14", "impureza_percentual":"0", "defeitos_percentual":"0", "data_entrada":"2026-10-05", "versao":entrada["versao"], "motivo":"Corrigir nome"}
        r=self.client.patch(url,dados,format="json",HTTP_IDEMPOTENCY_KEY=str(uuid4()))
        self.assertEqual(r.status_code,200,r.data)
        self.assertEqual(MovimentoProducaoTerceiro.objects.get(tipo="edicao").delta_kg,Decimal("0"))
        usuario=get_user_model().objects.create_user("sem-editar-terceiros")
        AcessoUsuario.objects.create(usuario=usuario,modulos=["cargas"],permissoes={"cargas":["consultar","cadastrar"]})
        self.client.force_authenticate(usuario)
        self.assertEqual(self.client.patch(url,{**dados,"versao":r.data["versao"]},format="json",HTTP_IDEMPOTENCY_KEY=str(uuid4())).status_code,403)
        self.assertEqual(self.client.delete(url,{"motivo":"Excluir","data_movimento":"2026-10-05"},format="json",HTTP_IDEMPOTENCY_KEY=str(uuid4())).status_code,403)

    def saida(self, entrada, peso, chave=None):
        return self.client.post(f"/api/graos/terceiros/entradas/{entrada}/registrar-saida/", {"quantidade_kg":peso, "destino":"Depositante", "data_movimento":"2026-10-05"}, format="json", HTTP_IDEMPOTENCY_KEY=chave or str(uuid4()))

    def transferir(self, entrada, peso="200", chave=None, **alteracoes):
        dados = {"versao":entrada["versao"], "propriedade":self.propriedade.pk,
                 "cad_pro":str(self.cad_pro.pk), "quantidade_kg":peso, "data_movimento":"2026-10-06", **alteracoes}
        return self.client.post(f"/api/graos/terceiros/entradas/{entrada['id']}/transferir/", dados,
                                format="json", HTTP_IDEMPOTENCY_KEY=chave or str(uuid4()))

    def test_transferencia_conserva_estoque_sem_producao_e_reenvio(self):
        registrar_carga_colhida(usuario=self.usuario, **self.dados_carga())
        antes = selecionar_relatorio_operacional(secao="produtividade", pagina=1, por_pagina=25)
        painel = construir_painel(self.usuario)
        entrada = self.entrada().data
        ocupacao = saldo_armazem(self.armazem)
        chave = str(uuid4())
        resposta = self.transferir(entrada, chave=chave)
        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.assertEqual(Decimal(resposta.data["saldo_kg"]), Decimal("400"))
        movimento = MovimentoProducaoTerceiro.objects.get(tipo="transferencia")
        oficial = movimento.movimentacao_saldo
        self.assertEqual(oficial.operacao, MovimentacaoGraos.Operacao.AJUSTE)
        self.assertEqual(oficial.posicao.propriedade_id, self.propriedade.pk)
        self.assertEqual(oficial.posicao.cad_pro_id, self.cad_pro.pk)
        self.assertEqual(oficial.posicao.saldo_fisico_kg, Decimal("200"))
        self.assertEqual(oficial.posicao.cultura, "Milho")
        self.assertEqual(saldo_armazem(self.armazem), ocupacao)
        depois = selecionar_relatorio_operacional(secao="produtividade", pagina=1, por_pagina=25)
        for campo in ("dados", "totais_producao_propriedade", "produtividade_por_cad_pro"):
            self.assertEqual(antes[campo], depois[campo])
        self.assertEqual(construir_painel(self.usuario)["resumo"]["producao_kg"], painel["resumo"]["producao_kg"])
        self.assertEqual(self.transferir(entrada, chave=chave).status_code, 200)
        self.assertEqual(MovimentoProducaoTerceiro.objects.filter(tipo="transferencia").count(), 1)
        self.assertEqual(self.transferir(entrada, peso="201", chave=chave).status_code, 400)
        self.assertEqual(self.transferir(entrada).status_code, 400)  # versão antiga
        estorno = self.estornar(movimento.pk)
        self.assertEqual(estorno.status_code, 201, estorno.data)
        self.assertEqual(Decimal(estorno.data["saldo_kg"]), Decimal("600"))
        oficial.posicao.refresh_from_db()
        self.assertEqual(oficial.posicao.saldo_fisico_kg, Decimal("0"))
        self.assertEqual(saldo_armazem(self.armazem), ocupacao)
        self.assertEqual(self.estornar(movimento.pk).status_code, 400)

    def test_transferencia_armazem_cheio_e_saldo_insuficiente(self):
        entrada = self.entrada("100000").data
        self.assertEqual(self.transferir(entrada, "100001").status_code, 400)
        resposta = self.transferir(entrada, "100000")
        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.assertEqual(Decimal(resposta.data["saldo_kg"]), Decimal("0"))
        self.assertEqual(saldo_armazem(self.armazem), Decimal("100000"))

    def test_transferencia_destino_invalido_e_rollback(self):
        from apps.cadpro.models import CADPro
        from unittest.mock import patch
        from .services import SaldoGraosError
        entrada = self.entrada().data
        outro = CADPro.objects.create(codigo="SEM-VINCULO", descricao="Sem vínculo")
        self.assertEqual(self.transferir(entrada, cad_pro=str(outro.pk)).status_code, 400)
        self.cad_pro.ativo = False
        self.cad_pro.save()
        self.assertEqual(self.transferir(entrada).status_code, 400)
        self.cad_pro.ativo = True
        self.cad_pro.save()
        with patch("apps.graos.terceiros.registrar_ajuste", side_effect=SaldoGraosError("Falha no crédito")):
            self.assertEqual(self.transferir(entrada).status_code, 400)
        salvo = EntradaProducaoTerceiro.objects.get(pk=entrada["id"])
        self.assertEqual(salvo.saldo_kg, Decimal("600"))
        self.assertEqual(salvo.versao, entrada["versao"])
        self.assertFalse(MovimentacaoGraos.objects.exists())
        self.assertFalse(MovimentoProducaoTerceiro.objects.filter(tipo="transferencia").exists())

    def test_estorno_transferencia_bloqueia_reserva_e_atalho_ledger(self):
        from .services import reservar_saldo, estornar_movimentacao, SaldoGraosError
        self.transferir(self.entrada().data)
        movimento = MovimentoProducaoTerceiro.objects.get(tipo="transferencia")
        oficial = movimento.movimentacao_saldo
        with self.assertRaises(SaldoGraosError):
            estornar_movimentacao(usuario=self.usuario, movimentacao=oficial, chave_idempotencia=str(uuid4()))
        reservar_saldo(usuario=self.usuario, lote=oficial.lote, quantidade_kg="100", chave_idempotencia=str(uuid4()))
        self.assertEqual(self.estornar(movimento.pk).status_code, 400)
        movimento.entrada.refresh_from_db()
        oficial.posicao.refresh_from_db()
        self.assertEqual(movimento.entrada.saldo_kg, Decimal("400"))
        self.assertEqual(oficial.posicao.saldo_fisico_kg, Decimal("200"))
        self.assertFalse(MovimentoProducaoTerceiro.objects.filter(estorno_de=movimento).exists())
        self.assertFalse(MovimentacaoGraos.objects.filter(estorno_de=oficial).exists())

    def test_estorno_reenviado_confere_permissao_atual(self):
        self.transferir(self.entrada().data)
        movimento = MovimentoProducaoTerceiro.objects.get(tipo="transferencia")
        usuario = get_user_model().objects.create_user("estorno-reenvio-terceiros")
        acesso = AcessoUsuario.objects.create(usuario=usuario, modulos=["cargas", "transferencias"], permissoes={"cargas":["consultar", "excluir"], "transferencias":["consultar", "excluir"]})
        self.client.force_authenticate(usuario)
        url = f"/api/graos/terceiros/movimentos/{movimento.pk}/estornar/"
        dados = {"motivo":"Conferência", "data_movimento":"2026-10-06"}
        chave = str(uuid4())
        self.assertEqual(self.client.post(url, dados, format="json", HTTP_IDEMPOTENCY_KEY=chave).status_code, 201)
        self.assertEqual(self.client.post(url, dados, format="json", HTTP_IDEMPOTENCY_KEY=chave).status_code, 200)
        acesso.permissoes["transferencias"] = ["consultar"]
        acesso.save()
        self.assertEqual(self.client.post(url, dados, format="json", HTTP_IDEMPOTENCY_KEY=chave).status_code, 403)

    def test_transferencia_exige_permissoes_das_duas_origens(self):
        entrada = self.entrada().data
        usuario = get_user_model().objects.create_user("terceiros-permissoes")
        acesso = AcessoUsuario.objects.create(usuario=usuario, modulos=["cargas", "transferencias"], permissoes={"cargas":["consultar", "cadastrar", "excluir"], "transferencias":["consultar"]})
        self.client.force_authenticate(usuario)
        self.assertEqual(self.transferir(entrada).status_code, 403)
        acesso.permissoes = {"cargas":["consultar"], "transferencias":["consultar", "cadastrar", "excluir"]}
        acesso.save()
        self.assertEqual(self.transferir(entrada).status_code, 403)
        self.client.force_authenticate(self.usuario)
        self.assertEqual(self.transferir(entrada).status_code, 201)
        movimento = MovimentoProducaoTerceiro.objects.get(tipo="transferencia")
        self.client.force_authenticate(usuario)
        self.assertEqual(self.estornar(movimento.pk).status_code, 403)
        acesso.permissoes = {"cargas":["consultar", "excluir"], "transferencias":["consultar"]}
        acesso.save()
        self.assertEqual(self.estornar(movimento.pk).status_code, 403)
        self.assertFalse(MovimentoProducaoTerceiro.objects.filter(estorno_de=movimento).exists())

    def estornar(self, movimento):
        return self.client.post(f"/api/graos/terceiros/movimentos/{movimento}/estornar/", {"motivo":"Conferência", "data_movimento":"2026-10-05"}, format="json", HTTP_IDEMPOTENCY_KEY=str(uuid4()))

    def test_entrada_estoque_e_produtividade_separados(self):
        registrar_carga_colhida(usuario=self.usuario, **self.dados_carga())
        antes=selecionar_relatorio_operacional(secao="produtividade", pagina=1, por_pagina=25)
        painel=construir_painel(self.usuario)
        saldos=list(PosicaoSaldoGraos.objects.values("saldo_fisico_kg", "saldo_comprometido_kg"))
        movimentos=MovimentacaoGraos.objects.count()
        resposta=self.entrada()
        self.assertEqual(resposta.status_code,201,resposta.data)
        self.assertEqual(Decimal(resposta.data["saldo_kg"]),Decimal("600"))
        self.assertEqual(saldo_armazem(self.armazem),Decimal("1575"))
        self.assertEqual(list(PosicaoSaldoGraos.objects.values("saldo_fisico_kg", "saldo_comprometido_kg")),saldos)
        self.assertEqual(MovimentacaoGraos.objects.count(),movimentos)
        depois=selecionar_relatorio_operacional(secao="produtividade", pagina=1, por_pagina=25)
        for campo in ("totais","dados","totais_producao_propriedade","produtividade_por_cad_pro"):
            self.assertEqual(antes[campo],depois[campo])
        atualizado=construir_painel(self.usuario)
        self.assertEqual(atualizado["resumo"]["producao_kg"],painel["resumo"]["producao_kg"])
        self.assertEqual(Decimal(atualizado["resumo"]["saldo_terceiros_kg"]),Decimal("600"))
        self.assertEqual(Decimal(atualizado["resumo"]["estoque_total_kg"]),Decimal("1575"))
        self.assertNotIn("saldo_terceiros_kg",construir_painel(self.usuario,propriedade=self.propriedade.pk)["resumo"])

    def test_retirada_estornos_saldo_e_historico(self):
        resposta=self.entrada();pk=resposta.data["id"]
        entrada_mov=resposta.data["movimentos"][0]["id"]
        self.assertEqual(self.saida(pk,"601").status_code,400)
        chave=str(uuid4());saida=self.saida(pk,"200",chave)
        self.assertEqual(saida.status_code,201,saida.data)
        self.assertEqual(self.saida(pk,"200",chave).status_code,200)
        self.assertEqual(self.saida(pk,"201",chave).status_code,400)
        saida_mov=next(m["id"] for m in saida.data["movimentos"] if m["tipo"]=="saida")
        self.assertEqual(self.estornar(entrada_mov).status_code,400)
        self.assertEqual(self.estornar(saida_mov).status_code,201)
        self.assertEqual(self.estornar(saida_mov).status_code,400)
        self.assertEqual(self.estornar(entrada_mov).status_code,201)
        self.assertEqual(self.saida(pk,"1").status_code,400)
        self.assertEqual(saldo_armazem(self.armazem),Decimal("0"))
        self.assertEqual(MovimentoProducaoTerceiro.objects.count(),4)
        with self.assertRaises(ValidationError):
            MovimentoProducaoTerceiro.objects.first().delete()

    def test_idempotencia_entrada_e_capacidade_compartilhada(self):
        chave=str(uuid4())
        self.assertEqual(self.entrada("99000",chave).status_code,201)
        self.assertEqual(self.entrada("99000",chave).status_code,200)
        self.assertEqual(EntradaProducaoTerceiro.objects.count(),1)
        self.assertEqual(self.entrada("99001",chave).status_code,400)
        self.assertEqual(self.entrada("1001").status_code,400)
        dados=self.dados_carga();dados["peso_bruto_kg"]="2000"
        with self.assertRaises((CapacidadeArmazemExcedidaError,CargaColhidaError)):
            registrar_carga_colhida(usuario=self.usuario,**dados)

    def test_permissoes_e_peso_invalido(self):
        self.assertEqual(self.entrada("0").status_code,400)
        self.assertEqual(self.entrada("-2").status_code,400)
        usuario=get_user_model().objects.create_user("consulta-terceiros")
        acesso=AcessoUsuario.objects.create(usuario=usuario,modulos=["cargas"],permissoes={"cargas":["consultar"]})
        self.client.force_authenticate(usuario)
        self.assertEqual(self.client.get("/api/graos/terceiros/entradas/").status_code,200)
        self.assertEqual(self.entrada().status_code,403)
        acesso.modulos=[];acesso.save()
        self.assertEqual(self.client.get("/api/graos/terceiros/entradas/").status_code,403)


@skipUnless(connection.vendor == "postgresql", "Requer bloqueios reais do PostgreSQL.")
class TerceirosConcorrenciaTests(CargaColhidaBase, TransactionTestCase):
    def setUp(self):
        self.criar_contexto()
        self.entrada, _ = executar_terceiro(usuario=self.usuario, tipo="entrada", dados={"depositante":"Terceiro", "cultura":"Milho", "safra":"2026", "armazem":self.armazem, "peso_liquido_kg":Decimal("600"), "data_entrada":date(2026,10,5)}, chave=str(uuid4()))

    def retirar(self, chave, barreira):
        close_old_connections()
        try:
            usuario=get_user_model().objects.get(pk=self.usuario.pk)
            barreira.wait(timeout=10)
            try:
                executar_terceiro(usuario=usuario,tipo="saida",pk=self.entrada.pk,dados={"quantidade_kg":Decimal("400"),"data_movimento":date(2026,10,5),"destino":"Depositante"},chave=chave)
                return True
            except APIValidationError:
                return False
        finally:
            close_old_connections()

    def concorrer(self, chaves):
        barreira=Barrier(2)
        with ThreadPoolExecutor(max_workers=2) as executor:
            futuros=[executor.submit(self.retirar,chave,barreira) for chave in chaves]
            return [f.result(timeout=20) for f in futuros]

    def test_saidas_concorrentes_nao_consumem_saldo_duas_vezes(self):
        self.assertEqual(sorted(self.concorrer([str(uuid4()),str(uuid4())])),[False,True])
        self.entrada.refresh_from_db()
        self.assertEqual(self.entrada.saldo_kg,Decimal("200"))
        self.assertEqual(MovimentoProducaoTerceiro.objects.filter(tipo="saida").count(),1)

    def test_reenvio_concorrente_idempotente(self):
        chave=str(uuid4())
        self.assertEqual(self.concorrer([chave,chave]),[True,True])
        self.entrada.refresh_from_db()
        self.assertEqual(self.entrada.saldo_kg,Decimal("200"))
        self.assertEqual(MovimentoProducaoTerceiro.objects.filter(tipo="saida").count(),1)

    def transferir_concorrente(self, chave, barreira):
        close_old_connections()
        try:
            usuario = get_user_model().objects.get(pk=self.usuario.pk)
            dados = {"versao":1, "propriedade":self.propriedade, "cad_pro":self.cad_pro,
                     "quantidade_kg":Decimal("400"), "data_movimento":date(2026,10,6)}
            barreira.wait(timeout=10)
            try:
                executar_terceiro(usuario=usuario, tipo="transferencia", pk=self.entrada.pk, dados=dados, chave=chave)
                return True
            except APIValidationError:
                return False
        finally:
            close_old_connections()

    def test_transferencias_concorrentes_e_reenvio(self):
        for mesma_chave in (False, True):
            if mesma_chave:
                # Outro recebimento mantém o primeiro histórico intacto.
                self.entrada, _ = executar_terceiro(usuario=self.usuario, tipo="entrada", dados={"depositante":"Outro", "cultura":"Milho", "safra":"2026", "armazem":self.armazem, "peso_liquido_kg":Decimal("600"), "data_entrada":date(2026,10,5)}, chave=str(uuid4()))
            barreira = Barrier(2)
            chave = str(uuid4())
            with ThreadPoolExecutor(max_workers=2) as executor:
                futuros = [executor.submit(self.transferir_concorrente, chave if mesma_chave else str(uuid4()), barreira) for _ in range(2)]
                resultados = [f.result(timeout=20) for f in futuros]
            self.assertEqual(sorted(resultados), [True, True] if mesma_chave else [False, True])
            self.entrada.refresh_from_db()
            self.assertEqual(self.entrada.saldo_kg, Decimal("200"))
            self.assertEqual(self.entrada.movimentos.filter(tipo="transferencia").count(), 1)

    def test_retirada_e_transferencia_concorrentes(self):
        barreira = Barrier(2)
        with ThreadPoolExecutor(max_workers=2) as executor:
            futuros = [executor.submit(funcao, str(uuid4()), barreira) for funcao in (self.retirar, self.transferir_concorrente)]
            self.assertEqual(sorted(f.result(timeout=20) for f in futuros), [False, True])
        self.entrada.refresh_from_db()
        self.assertEqual(self.entrada.saldo_kg, Decimal("200"))
        self.assertEqual(self.entrada.movimentos.filter(tipo__in=("saida", "transferencia")).count(), 1)

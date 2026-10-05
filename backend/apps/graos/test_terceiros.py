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

    def saida(self, entrada, peso, chave=None):
        return self.client.post(f"/api/graos/terceiros/entradas/{entrada}/registrar-saida/", {"quantidade_kg":peso, "destino":"Depositante", "data_movimento":"2026-10-05"}, format="json", HTTP_IDEMPOTENCY_KEY=chave or str(uuid4()))

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

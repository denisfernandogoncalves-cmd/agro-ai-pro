from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase
from rest_framework.test import APITestCase

from .codigos import CodigoPagamentoInvalido, ler_codigo_pagamento, modulo10, modulo11
from .models import CategoriaFinanceira, LancamentoFinanceiro

# Exemplares sintéticos fixos: não representam documentos a pagar.
BOLETO = "00197100000000123451234567890123456789012345"
LINHA = "00191234546789012345767890123457710000000012345"
ARRECADACAO = {
    "6": ("83670000001234512342026091000000000000000000", "836700000018234512342028609100000007000000000000"),
    "7": ("83750000001234512342026091000000000000000000", "837500000018234512342028609100000007000000000000"),
    "8": ("83800000001234512342026091000000000000000000", "838000000017234512342021609100000004000000000000"),
    "9": ("83980000001234512342026091000000000000000000", "839800000010234512342021609100000004000000000000"),
}


class LeituraCodigoTests(SimpleTestCase):
    def test_linha_reconstruida_detalhes_e_descricao(self):
        resultado = ler_codigo_pagamento(BOLETO)
        self.assertEqual(resultado["linha_digitavel"], LINHA)
        self.assertEqual(ler_codigo_pagamento(resultado["linha_digitavel_formatada"])["codigo_barras"], BOLETO)
        detalhes = {item["campo"]: item["valor"] for item in resultado["detalhes"]}
        self.assertEqual(detalhes["Campo livre do banco"], "1234567890123456789012345")
        self.assertEqual(detalhes["Fator de vencimento"], "1000")
        self.assertEqual(resultado["descricao_sugerida"], "Boleto bancário · Banco do Brasil S.A. (001)")
        for barras, linha in ARRECADACAO.values():
            resultado = ler_codigo_pagamento(barras)
            self.assertEqual(resultado["linha_digitavel"], linha)
            self.assertEqual(ler_codigo_pagamento(resultado["linha_digitavel_formatada"])["codigo_barras"], barras)

    def test_banco_iniciado_em_oito_e_boleto_sem_valor(self):
        resultado = ler_codigo_pagamento("85597100000000123451234567890123456789012345")
        self.assertEqual(resultado["tipo"], "boleto")
        self.assertEqual(resultado["banco_codigo"], "855")
        resultado = ler_codigo_pagamento("00196100000000000001234567890123456789012345")
        self.assertIsNone(resultado["valor"])

    def test_nome_do_banco_sem_inventar_recebedor(self):
        resultado = ler_codigo_pagamento(BOLETO)
        self.assertEqual(resultado["banco_nome"], "Banco do Brasil S.A.")
        self.assertNotIn("recebedor_nome", resultado)
        self.assertTrue(any("não é o recebedor" in aviso for aviso in resultado["avisos"]))
        desconhecido = "9999" + BOLETO[4:]
        desconhecido = desconhecido[:4] + str(modulo11(desconhecido[:4] + desconhecido[5:])) + desconhecido[5:]
        resultado = ler_codigo_pagamento(desconhecido)
        self.assertIsNone(resultado["banco_nome"])
        self.assertEqual(resultado["banco_codigo"], "999")
        self.assertIsNone(ler_codigo_pagamento(ARRECADACAO["6"][0])["banco_nome"])

    def test_itau_extrai_apenas_layout_com_digitos_coerentes(self):
        # Dados sintéticos; exemplo agência/conta do manual, sem título real.
        agencia, conta, carteira, numero = "0057", "12345", "112", "12345678"
        livre = carteira + numero + str(modulo10(agencia + conta + carteira + numero))
        livre += agencia + conta + str(modulo10(agencia + conta)) + "000"

        def boleto_com_campo(campo):
            base = "3419" + "1000" + "0000012345" + campo
            return base[:4] + str(modulo11(base)) + base[4:]

        boleto = boleto_com_campo(livre)
        resultado = ler_codigo_pagamento(boleto)
        self.assertIn("ITAÚ", resultado["banco_nome"].upper())
        detalhes = {item["campo"]: item["valor"] for item in resultado["detalhes"]}
        self.assertEqual(detalhes["Agência do beneficiário"], "0057")
        self.assertEqual(detalhes["Conta do beneficiário"], "12345-7")
        self.assertEqual(detalhes["Carteira"], "112")
        self.assertTrue(detalhes["Nosso número"].startswith("12345678-"))
        self.assertEqual(ler_codigo_pagamento(resultado["linha_digitavel"])["detalhes"], resultado["detalhes"])
        for campo in ("198" + livre[3:], livre[:-1] + "1", livre[:11] + str((int(livre[11]) + 1) % 10) + livre[12:],
                      livre[:21] + str((int(livre[21]) + 1) % 10) + livre[22:]):
            with self.subTest(campo=campo):
                sem_layout = ler_codigo_pagamento(boleto_com_campo(campo))
                self.assertNotIn("Agência do beneficiário", {item["campo"] for item in sem_layout["detalhes"]})
                self.assertEqual(sem_layout["valor"], "123.45")

    def test_boleto_barras_linha_e_formatacao_equivalentes(self):
        esperado = ler_codigo_pagamento(BOLETO)
        esperado.pop("formato_entrada")
        da_linha = ler_codigo_pagamento(LINHA)
        self.assertEqual(da_linha.pop("formato_entrada"), "Linha digitável (47 dígitos)")
        self.assertEqual(esperado, da_linha)
        formatado = ler_codigo_pagamento(f"{LINHA[:5]}.{LINHA[5:10]} {LINHA[10:]}\r\n")
        formatado.pop("formato_entrada")
        self.assertEqual(esperado, formatado)
        self.assertEqual(esperado["valor"], "123.45")
        self.assertEqual(esperado["banco_codigo"], "001")
        self.assertEqual(esperado["vencimentos_possiveis"], ["2025-02-22", "2000-07-03"])

    def test_limite_fator_e_sem_vencimento(self):
        resultado = ler_codigo_pagamento("00191999900000123451234567890123456789012345")
        self.assertEqual(resultado["vencimentos_possiveis"], ["2049-10-13", "2025-02-21"])
        resultado = ler_codigo_pagamento("00194000000000123451234567890123456789012345")
        self.assertEqual(resultado["vencimentos_possiveis"], [])

    def test_arrecadacao_modulos_valores_e_referencias(self):
        for indicador, (barras, linha) in ARRECADACAO.items():
            with self.subTest(indicador=indicador):
                resultado = ler_codigo_pagamento(barras)
                da_linha = ler_codigo_pagamento(linha)
                resultado.pop("formato_entrada")
                da_linha.pop("formato_entrada")
                self.assertEqual(resultado, da_linha)
                self.assertEqual(resultado["tipo"], "arrecadacao")
                self.assertEqual(resultado["segmento"], "Energia elétrica e gás")
                self.assertEqual(resultado["identificacao_emissor"], "1234")
                self.assertEqual(resultado["valor"], "123.45" if indicador in "68" else None)
                # Uma data aparente no campo livre não comprova o vencimento.
                self.assertEqual(resultado["vencimentos_possiveis"], [])

    def test_digitos_dos_campos_e_geral_invalidos(self):
        for codigo, indices in ((BOLETO, [4, 12]), (LINHA, [9, 20, 31, 32]),
                                (ARRECADACAO["6"][1], [11, 23, 35, 47]),
                                (ARRECADACAO["8"][0], [3])):
            for indice in indices:
                alterado = codigo[:indice] + str((int(codigo[indice]) + 1) % 10) + codigo[indice + 1:]
                with self.subTest(codigo=codigo, indice=indice), self.assertRaises(CodigoPagamentoInvalido):
                    ler_codigo_pagamento(alterado)

    def test_rejeita_outros_codigos_e_entradas_malformadas(self):
        for codigo in (None, 123, {}, "", "0" * 44, "1" * 47, "123", "9" * 101,
                       "https://exemplo.com/" + BOLETO, "A" + BOLETO, "３" * 44,
                       "000201010212PIX", BOLETO + "1", LINHA + "1"):
            with self.subTest(codigo=codigo), self.assertRaises(CodigoPagamentoInvalido):
                ler_codigo_pagamento(codigo)

    def test_modulos_exemplos_e_excecoes(self):
        # Exemplo módulo 11 do manual FEBRABAN: soma 176, resto zero.
        self.assertEqual(modulo11("01230067896", arrecadacao=True), 0)
        self.assertEqual(modulo11("0"), 1)
        self.assertEqual(modulo11("6"), 1)  # Resto 1 no boleto.
        self.assertEqual(modulo11("6", arrecadacao=True), 0)
        self.assertEqual(modulo11("5", arrecadacao=True), 1)  # Resto 10.
        self.assertEqual(modulo10("001905009"), 5)


class LeituraCodigoAPITests(APITestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(username="leitor-financeiro")
        self.client.force_authenticate(self.usuario)
        self.categoria = CategoriaFinanceira.objects.create(nome="Contas", aplicacao="despesa")
        self.url = "/api/financeiro/lancamentos/ler-codigo/"
        self.dados = {
            "tipo": "pagar", "descricao": "Boleto de teste", "valor": "123.45",
            "categoria": self.categoria.pk, "data_vencimento": "2026-09-30", "codigo_barras": LINHA,
        }

    def test_leitura_nao_grava_nem_liquida_e_exige_login(self):
        for _ in range(2):
            resposta = self.client.post(self.url, {"codigo": LINHA}, format="json")
            self.assertEqual(resposta.status_code, 200)
            self.assertEqual(resposta.data["codigo_barras"], BOLETO)
        self.assertFalse(LancamentoFinanceiro.objects.exists())
        self.client.force_authenticate(None)
        self.assertEqual(self.client.post(self.url, {"codigo": LINHA}).status_code, 401)

    def test_salva_normalizado_e_informa_duplicidade_na_previa(self):
        resposta = self.client.post("/api/financeiro/lancamentos/", self.dados, format="json")
        self.assertEqual(resposta.status_code, 201, resposta.data)
        lancamento = LancamentoFinanceiro.objects.get()
        self.assertEqual(lancamento.codigo_barras, BOLETO)
        self.assertEqual(lancamento.status, "pendente")
        self.assertEqual(lancamento.valor, Decimal("123.45"))
        previa = self.client.post(self.url, {"codigo": BOLETO}, format="json")
        self.assertEqual(previa.data["lancamentos_existentes"][0]["id"], lancamento.pk)
        self.assertEqual(LancamentoFinanceiro.objects.count(), 1)

    def test_api_rejeita_codigo_invalido_sem_gravar(self):
        self.assertEqual(self.client.post(self.url, [], format="json").status_code, 400)
        resposta = self.client.post(self.url, {"codigo": "123"}, format="json")
        self.assertEqual(resposta.status_code, 400)
        resposta = self.client.post("/api/financeiro/lancamentos/", {**self.dados, "codigo_barras": "123"}, format="json")
        self.assertEqual(resposta.status_code, 400)
        self.assertIn("codigo_barras", resposta.data)
        self.assertFalse(LancamentoFinanceiro.objects.exists())

    def test_lancamento_manual_e_atualizacao_preservam_compatibilidade(self):
        dados = {k: v for k, v in self.dados.items() if k != "codigo_barras"}
        resposta = self.client.post("/api/financeiro/lancamentos/", dados, format="json")
        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.assertEqual(resposta.data["codigo_barras"], "")
        url = f"/api/financeiro/lancamentos/{resposta.data['id']}/"
        self.assertEqual(self.client.patch(url, {"codigo_barras": LINHA}).status_code, 200)
        self.assertEqual(self.client.patch(url, {"descricao": "Conferido"}).data["codigo_barras"], BOLETO)

from datetime import date
from decimal import Decimal
from io import BytesIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from openpyxl import Workbook, load_workbook
from rest_framework.test import APITestCase

from apps.graos.models import (
    ArmazemGraos,
    LoteGraos,
    MovimentacaoGraos,
)
from apps.graos.services import saldo_lote
from apps.propriedades.models import Propriedade
from apps.cadpro.models import CADPro, CADProPropriedade

from .models import ConfirmacaoImportacao, LinhaImportacao, LoteImportacao
from .services import (
    ArquivoImportacaoDuplicadoError,
    PlanilhaImportacaoError,
    processar_preview_planilha,
)


def criar_planilha_teste(nome="preview-soja.xlsx"):
    workbook = Workbook()
    workbook.remove(workbook.active)

    producao = workbook.create_sheet("1")
    producao["C2"] = "Fazenda Modelo"
    producao["C3"] = 10
    producao["F3"] = "SOJA"
    producao["C4"] = "25/26"
    producao.append([])
    producao.append([])
    producao.append([])
    producao["B6"] = "DATA"
    producao["C6"] = "PLACA"
    producao["D6"] = "PESO (Kg)"
    producao["K6"] = "PESO LIQUIDO (Kg)"
    producao["B7"] = date(2026, 2, 1)
    producao["C7"] = "ABC 1D23"
    producao["D7"] = 1000
    producao["E7"] = 14
    producao["F7"] = 1
    producao["G7"] = 0
    producao["H7"] = 80
    producao["K7"] = 950
    producao["B8"] = "data-invalida"
    producao["D8"] = -1
    producao["K8"] = 0

    saida = workbook.create_sheet("SAÍDA")
    saida["C3"] = "SOJA"
    saida["C4"] = "25/26"
    saida["B6"] = "DATA"
    saida["C6"] = "DESTINO"
    saida["G6"] = "CADPRO"
    saida["L6"] = "PESO LIQUIDO (Kg)"
    saida["B7"] = date(2026, 3, 1)
    saida["C7"] = "C.VALE"
    saida["F7"] = "XYZ 9A99"
    saida["G7"] = "Fazenda Modelo"
    saida["H7"] = "Produtor"
    saida["I7"] = "C-100"
    saida["J7"] = "NP-10"
    saida["L7"] = 100

    terceiros = workbook.create_sheet("TERCEIROS")
    terceiros["C3"] = "SOJA"
    terceiros["C4"] = "25/26"
    terceiros["B6"] = "DATA"
    terceiros["C6"] = "PRODUTOR"
    terceiros["E6"] = "PESO (Kg)"
    terceiros["K6"] = "PESO LIQUIDO (Kg)"
    terceiros["B7"] = date(2026, 3, 2)
    terceiros["C7"] = "Terceiro sem cadastro"
    terceiros["E7"] = 500
    terceiros["F7"] = 14
    terceiros["G7"] = 1
    terceiros["H7"] = 0
    terceiros["I7"] = 80
    terceiros["K7"] = 490

    workbook.create_sheet("MENU")
    conteudo = BytesIO()
    workbook.save(conteudo)
    workbook.close()
    return SimpleUploadedFile(
        nome,
        conteudo.getvalue(),
        content_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
    )


class ImportacaoBase:
    def criar_contexto(self):
        self.usuario = get_user_model().objects.create_user("importador")
        self.propriedade = Propriedade.objects.create(
            nome="Fazenda Modelo",
            municipio="Sorriso",
            uf="MT",
            area_hectares="100",
        )
        self.armazem = ArmazemGraos.objects.create(
            propriedade=self.propriedade,
            nome="Silo Modelo",
            capacidade_kg="100000",
        )
        self.lote_graos = LoteGraos.objects.create(
            armazem=self.armazem,
            propriedade=self.propriedade,
            cad_pro=CADPro.objects.create(codigo="12345678", descricao="Importação"),
            codigo="SOJA-25-26",
            cultura="Soja",
            safra="2025/2026",
        )
        CADProPropriedade.objects.create(
            propriedade=self.propriedade, cad_pro=self.lote_graos.cad_pro,
        )


class ImportacaoServiceTests(ImportacaoBase, TestCase):
    def setUp(self):
        self.criar_contexto()

    def test_preview_persiste_lote_linhas_e_associacoes_sem_movimentar(self):
        saldo_antes = saldo_lote(self.lote_graos)
        lote = processar_preview_planilha(
            arquivo=criar_planilha_teste(),
            usuario=self.usuario,
        )
        self.assertEqual(lote.status, LoteImportacao.Status.COM_ERROS)
        self.assertEqual(lote.total_planilhas, 3)
        self.assertEqual(lote.total_linhas, 4)
        self.assertEqual(lote.total_validas, 2)
        self.assertEqual(lote.total_advertencias, 1)
        self.assertEqual(lote.total_erros, 1)
        self.assertFalse(lote.metadados["gera_movimentacoes"])
        self.assertEqual(lote.metadados["total_duplicadas"], 0)
        self.assertIn("1", lote.metadados["cabecalhos_reconhecidos"])

        producao = lote.linhas.get(planilha="1", linha_origem=7)
        self.assertEqual(producao.status, LinhaImportacao.Status.VALIDA)
        self.assertEqual(producao.propriedade, self.propriedade)
        self.assertEqual(producao.lote_graos, self.lote_graos)
        self.assertEqual(
            producao.associacao,
            LinhaImportacao.Associacao.LOTE_GRAOS,
        )
        self.assertEqual(
            producao.dados_normalizados["peso_liquido_kg"],
            "950",
        )
        self.assertEqual(
            producao.dados_normalizados["classificacao_codigo"],
            "PADRAO",
        )

        invalida = lote.linhas.get(planilha="1", linha_origem=8)
        self.assertEqual(invalida.status, LinhaImportacao.Status.ERRO)
        self.assertGreaterEqual(len(invalida.erros), 3)

        terceiros = lote.linhas.get(planilha="TERCEIROS")
        self.assertEqual(
            terceiros.status,
            LinhaImportacao.Status.ADVERTENCIA,
        )
        self.assertTrue(terceiros.advertencias)
        self.assertEqual(MovimentacaoGraos.objects.count(), 0)
        self.assertEqual(saldo_lote(self.lote_graos), saldo_antes)

    def test_linha_repetida_e_sinalizada_sem_ser_descartada(self):
        arquivo = criar_planilha_teste()
        conteudo = BytesIO(arquivo.read())
        workbook = load_workbook(conteudo)
        producao = workbook["1"]
        for coluna in range(2, 12):
            producao.cell(9, coluna).value = producao.cell(7, coluna).value
        repetida = BytesIO()
        workbook.save(repetida)
        workbook.close()

        lote = processar_preview_planilha(
            arquivo=SimpleUploadedFile(
                "preview-com-duplicidade.xlsx",
                repetida.getvalue(),
            ),
            usuario=self.usuario,
        )
        linha = lote.linhas.get(planilha="1", linha_origem=9)
        self.assertEqual(linha.status, LinhaImportacao.Status.ADVERTENCIA)
        self.assertTrue(
            any("potencialmente duplicada" in aviso for aviso in linha.advertencias)
        )
        self.assertEqual(lote.total_linhas, 5)
        self.assertEqual(MovimentacaoGraos.objects.count(), 0)

    def test_hash_impede_reimportacao_do_mesmo_arquivo(self):
        primeiro = criar_planilha_teste()
        conteudo = primeiro.read()
        lote = processar_preview_planilha(
            arquivo=SimpleUploadedFile("preview-soja.xlsx", conteudo),
            usuario=self.usuario,
        )
        with self.assertRaises(ArquivoImportacaoDuplicadoError) as contexto:
            processar_preview_planilha(
                arquivo=SimpleUploadedFile("preview-soja.xlsx", conteudo),
                usuario=self.usuario,
            )
        self.assertEqual(contexto.exception.lote, lote)
        self.assertEqual(LoteImportacao.objects.count(), 1)

    def test_rejeita_extensao_invalida(self):
        arquivo = SimpleUploadedFile(
            "dados.csv",
            b"conteudo",
            content_type="text/csv",
        )
        with self.assertRaisesMessage(PlanilhaImportacaoError, ".xlsx"):
            processar_preview_planilha(
                arquivo=arquivo,
                usuario=self.usuario,
            )

    def test_rejeita_xlsx_corrompido(self):
        arquivo = SimpleUploadedFile(
            "dados.xlsx",
            b"nao-e-um-zip",
            content_type=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
        )
        with self.assertRaisesMessage(PlanilhaImportacaoError, "XLSX válido"):
            processar_preview_planilha(
                arquivo=arquivo,
                usuario=self.usuario,
            )


    def test_rejeita_layout_sem_cabecalhos_obrigatorios(self):
        arquivo = criar_planilha_teste()
        conteudo = BytesIO(arquivo.read())
        workbook = load_workbook(conteudo)
        workbook["1"]["K6"] = None
        invalida = BytesIO()
        workbook.save(invalida)
        workbook.close()

        with self.assertRaisesMessage(
            PlanilhaImportacaoError,
            "cabecalhos obrigatorios",
        ):
            processar_preview_planilha(
                arquivo=SimpleUploadedFile(
                    "layout-invalido.xlsx",
                    invalida.getvalue(),
                ),
                usuario=self.usuario,
            )


class ImportacaoApiTests(ImportacaoBase, APITestCase):
    def setUp(self):
        self.criar_contexto()
        self.client.force_authenticate(self.usuario)

    def test_autenticacao_e_obrigatoria(self):
        self.client.force_authenticate(None)
        self.assertEqual(
            self.client.get("/api/importacoes/lotes/").status_code,
            401,
        )
        self.assertEqual(
            self.client.get("/api/importacoes/linhas/").status_code,
            401,
        )
        self.assertEqual(
            self.client.post("/api/importacoes/lotes/preview/", {}).status_code,
            401,
        )

    def test_preview_e_consulta_auditavel(self):
        resposta = self.client.post(
            "/api/importacoes/lotes/preview/",
            {"arquivo": criar_planilha_teste()},
            format="multipart",
        )
        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.assertIn("no-store", resposta["Cache-Control"])
        self.assertIn("private", resposta["Cache-Control"])
        lote_id = resposta.data["lote"]["id"]
        self.assertEqual(resposta.data["lote"]["total_linhas"], 4)
        self.assertEqual(len(resposta.data["linhas_preview"]), 4)
        self.assertFalse(resposta.data["preview_limitado"])

        linhas = self.client.get(
            f"/api/importacoes/linhas/?lote={lote_id}&tipo=producao"
        )
        self.assertEqual(linhas.status_code, 200)
        self.assertEqual(len(linhas.data), 2)
        self.assertEqual(MovimentacaoGraos.objects.count(), 0)

    def test_upload_duplicado_retorna_409_e_lote_existente(self):
        arquivo = criar_planilha_teste()
        conteudo = arquivo.read()
        primeira = self.client.post(
            "/api/importacoes/lotes/preview/",
            {"arquivo": SimpleUploadedFile("preview-soja.xlsx", conteudo)},
            format="multipart",
        )
        repetida = self.client.post(
            "/api/importacoes/lotes/preview/",
            {"arquivo": SimpleUploadedFile("preview-soja.xlsx", conteudo)},
            format="multipart",
        )
        self.assertEqual(primeira.status_code, 201)
        self.assertEqual(repetida.status_code, 409)
        self.assertEqual(
            repetida.data["lote_existente"],
            primeira.data["lote"]["id"],
        )

    def test_lotes_e_linhas_sao_imutaveis_pela_api(self):
        lote = processar_preview_planilha(
            arquivo=criar_planilha_teste(),
            usuario=self.usuario,
        )
        linha = lote.linhas.first()
        self.assertEqual(
            self.client.patch(
                f"/api/importacoes/lotes/{lote.id}/",
                {"status": "concluido"},
                format="json",
            ).status_code,
            405,
        )
        self.assertEqual(
            self.client.delete(
                f"/api/importacoes/linhas/{linha.id}/"
            ).status_code,
            405,
        )

    def test_openapi_documenta_endpoint_de_preview(self):
        resposta = self.client.get("/api/schema.json")
        self.assertEqual(resposta.status_code, 200)
        self.assertIn(
            "/importacoes/lotes/preview/",
            resposta.data["paths"],
        )


class ConfirmacaoImportacaoApiTests(ImportacaoBase, APITestCase):
    endpoint_key = "confirmacao-api-0001"

    def setUp(self):
        self.criar_contexto()
        self.permissao = Permission.objects.get(
            codename="confirmar_loteimportacao",
        )
        self.usuario.user_permissions.add(self.permissao)
        self.client.force_authenticate(self.usuario)

    def criar_lote_confirmavel(self, linhas=None, **campos_lote):
        campos = {
            "arquivo_nome": "confirmacao.xlsx",
            "arquivo_tamanho": 100,
            "arquivo_sha256": f"{LoteImportacao.objects.count() + 1:064x}",
            "status": LoteImportacao.Status.PRONTO_PARA_CONFIRMACAO,
            "total_planilhas": 1,
            "total_linhas": len(linhas or [{}]),
            "total_validas": len(linhas or [{}]),
            "total_advertencias": 0,
            "total_erros": 0,
            "metadados": {"gera_movimentacoes": False},
            "criado_por": self.usuario,
        }
        campos.update(campos_lote)
        lote = LoteImportacao.objects.create(**campos)
        for sequencia, dados_linha in enumerate(linhas or [{}], start=1):
            tipo = dados_linha.get("tipo", LinhaImportacao.Tipo.PRODUCAO)
            normalizados = {
                "propriedade_nome": self.propriedade.nome,
                "cultura": self.lote_graos.cultura,
                "safra": self.lote_graos.safra,
                "data": "2026-03-01",
                "peso_liquido_kg": "100.000",
                "unidade": "kg",
            }
            if tipo == LinhaImportacao.Tipo.SAIDA:
                normalizados["destino"] = "Comprador"
            elif tipo == LinhaImportacao.Tipo.TERCEIROS:
                normalizados["produtor"] = "Produtor terceiro"
            normalizados.update(dados_linha.get("dados_normalizados", {}))
            LinhaImportacao.objects.create(
                lote_importacao=lote,
                sequencia=sequencia,
                planilha=dados_linha.get("planilha", "1"),
                linha_origem=dados_linha.get("linha_origem", sequencia + 6),
                tipo=tipo,
                status=dados_linha.get(
                    "status",
                    LinhaImportacao.Status.VALIDA,
                ),
                hash_linha=dados_linha.get(
                    "hash_linha",
                    f"{lote.id:016x}{sequencia:048x}",
                ),
                dados_originais={"origem": "preservada"},
                dados_normalizados=normalizados,
                erros=dados_linha.get("erros", []),
                advertencias=dados_linha.get("advertencias", []),
                associacao=(
                    LinhaImportacao.Associacao.LOTE_GRAOS
                    if dados_linha.get("lote_graos", self.lote_graos)
                    else LinhaImportacao.Associacao.NAO_ASSOCIADA
                ),
                propriedade=dados_linha.get("propriedade", self.propriedade),
                lote_graos=dados_linha.get("lote_graos", self.lote_graos),
            )
        return lote

    def confirmar(self, lote, key=None, confirmar=True):
        return self.client.post(
            f"/api/importacoes/lotes/{lote.id}/confirmar/",
            {
                "confirmar": confirmar,
                "idempotency_key": key or self.endpoint_key,
            },
            format="json",
        )

    def test_confirmacao_valida_cria_movimentacoes_e_vinculos(self):
        lote = self.criar_lote_confirmavel(
            [
                {"dados_normalizados": {"peso_liquido_kg": "500.000"}},
                {
                    "tipo": LinhaImportacao.Tipo.SAIDA,
                    "planilha": "SAÍDA",
                    "dados_normalizados": {"peso_liquido_kg": "100.000"},
                },
            ]
        )

        resposta = self.confirmar(lote)

        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.assertEqual(resposta.data["status"], LoteImportacao.Status.CONFIRMADO)
        self.assertEqual(resposta.data["total_movimentacoes_criadas"], 2)
        self.assertEqual(resposta.data["linhas_rejeitadas"], 0)
        self.assertFalse(resposta.data["replay_idempotente"])
        self.assertEqual(MovimentacaoGraos.objects.count(), 2)
        self.assertEqual(
            lote.linhas.filter(movimentacao_graos__isnull=False).count(),
            2,
        )
        self.assertEqual(saldo_lote(self.lote_graos), Decimal("400"))
        lote.refresh_from_db()
        self.assertEqual(lote.confirmado_por, self.usuario)
        self.assertIsNotNone(lote.confirmado_em)
        self.assertEqual(
            ConfirmacaoImportacao.objects.get().status,
            ConfirmacaoImportacao.Status.CONFIRMADA,
        )

    def test_replay_com_mesma_chave_retorna_resultado_sem_duplicar(self):
        lote = self.criar_lote_confirmavel()
        primeira = self.confirmar(lote)
        movimentos = list(MovimentacaoGraos.objects.values_list("id", flat=True))

        repetida = self.confirmar(lote)

        self.assertEqual(primeira.status_code, 201)
        self.assertEqual(repetida.status_code, 200, repetida.data)
        self.assertTrue(repetida.data["replay_idempotente"])
        self.assertEqual(repetida.data["movimentacoes_ids"], movimentos)
        self.assertEqual(MovimentacaoGraos.objects.count(), 1)
        self.assertEqual(ConfirmacaoImportacao.objects.count(), 1)

    def test_chave_diferente_apos_confirmacao_e_rejeitada(self):
        lote = self.criar_lote_confirmavel()
        self.assertEqual(self.confirmar(lote).status_code, 201)

        resposta = self.confirmar(lote, key="confirmacao-api-0002")

        self.assertEqual(resposta.status_code, 409)
        self.assertEqual(resposta.data["codigo"], "lote_ja_confirmado")
        self.assertEqual(MovimentacaoGraos.objects.count(), 1)

    def test_lote_com_erro_bloqueante_e_rejeitado(self):
        lote = self.criar_lote_confirmavel(
            [{"status": LinhaImportacao.Status.ERRO, "erros": ["peso inválido"]}],
            status=LoteImportacao.Status.COM_ERROS,
            total_validas=0,
            total_erros=1,
        )

        resposta = self.confirmar(lote)

        self.assertEqual(resposta.status_code, 409)
        self.assertEqual(resposta.data["codigo"], "lote_com_erros")
        self.assertEqual(MovimentacaoGraos.objects.count(), 0)

    def test_lote_nao_elegivel_e_rejeitado(self):
        lote = self.criar_lote_confirmavel(
            status=LoteImportacao.Status.CONFIRMANDO
        )
        resposta = self.confirmar(lote)
        self.assertEqual(resposta.status_code, 409)
        self.assertEqual(resposta.data["codigo"], "lote_nao_elegivel")

    def test_lote_inexistente_retorna_404(self):
        resposta = self.client.post(
            "/api/importacoes/lotes/999999/confirmar/",
            {"confirmar": True, "idempotency_key": self.endpoint_key},
            format="json",
        )
        self.assertEqual(resposta.status_code, 404)

    def test_confirmacao_exige_autenticacao(self):
        lote = self.criar_lote_confirmavel()
        self.client.force_authenticate(None)
        self.assertEqual(self.confirmar(lote).status_code, 401)

    def test_confirmacao_exige_permissao_especifica(self):
        lote = self.criar_lote_confirmavel()
        self.usuario.user_permissions.clear()
        self.assertEqual(self.confirmar(lote).status_code, 403)
        self.assertEqual(MovimentacaoGraos.objects.count(), 0)

    def test_chave_ausente_invalida_e_confirmacao_nao_explicita(self):
        lote = self.criar_lote_confirmavel()
        endpoint = f"/api/importacoes/lotes/{lote.id}/confirmar/"
        for corpo in (
            {"confirmar": True},
            {"confirmar": True, "idempotency_key": "curta"},
            {"confirmar": False, "idempotency_key": self.endpoint_key},
        ):
            resposta = self.client.post(endpoint, corpo, format="json")
            self.assertEqual(resposta.status_code, 400, resposta.data)
        self.assertEqual(MovimentacaoGraos.objects.count(), 0)

    def test_quantidade_propriedade_e_lote_graos_sao_bloqueantes(self):
        casos = (
            {"dados_normalizados": {"peso_liquido_kg": "0"}},
            {"propriedade": None},
            {"lote_graos": None},
        )
        for indice, caso in enumerate(casos, start=1):
            lote = self.criar_lote_confirmavel(
                [caso],
                arquivo_sha256=f"{100 + indice:064x}",
            )
            resposta = self.confirmar(
                lote,
                key=f"confirmacao-validacao-{indice:02d}",
            )
            self.assertEqual(resposta.status_code, 409, resposta.data)
            self.assertEqual(resposta.data["codigo"], "linhas_invalidas")
        self.assertEqual(MovimentacaoGraos.objects.count(), 0)

    def test_duplicidade_funcional_bloqueia_lote(self):
        lote = self.criar_lote_confirmavel(
            [
                {"hash_linha": "a" * 64},
                {"hash_linha": "a" * 64, "linha_origem": 8},
            ]
        )
        resposta = self.confirmar(lote)
        self.assertEqual(resposta.status_code, 409)
        self.assertEqual(resposta.data["codigo"], "linhas_invalidas")
        self.assertEqual(len(resposta.data["linhas_rejeitadas"]), 2)

    def test_duplicidade_funcional_ja_confirmada_e_bloqueada(self):
        primeiro = self.criar_lote_confirmavel(
            [{"hash_linha": "b" * 64}],
        )
        self.assertEqual(self.confirmar(primeiro).status_code, 201)
        segundo = self.criar_lote_confirmavel(
            [{"hash_linha": "b" * 64}],
            arquivo_sha256=f"{999:064x}",
        )

        resposta = self.confirmar(
            segundo,
            key="confirmacao-duplicada-0002",
        )

        self.assertEqual(resposta.status_code, 409)
        self.assertIn(
            "duplicidade funcional já confirmada",
            resposta.data["linhas_rejeitadas"][0]["erros"],
        )
        self.assertEqual(MovimentacaoGraos.objects.count(), 1)

    def test_status_legado_concluido_permanece_elegivel(self):
        lote = self.criar_lote_confirmavel(
            status=LoteImportacao.Status.CONCLUIDO,
        )
        resposta = self.confirmar(lote)
        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.assertEqual(resposta.data["status"], LoteImportacao.Status.CONFIRMADO)

    def test_falha_intermediaria_reverte_movimentos_saldos_e_vinculos(self):
        lote = self.criar_lote_confirmavel([{}, {"linha_origem": 8}])
        from apps.graos.services import registrar_movimentacao as oficial

        chamadas = 0

        def falhar_na_segunda(**dados):
            nonlocal chamadas
            chamadas += 1
            if chamadas == 2:
                raise RuntimeError("falha simulada")
            return oficial(**dados)

        with patch(
            "apps.importacoes.confirmation_services.registrar_movimentacao",
            side_effect=falhar_na_segunda,
        ):
            resposta = self.confirmar(lote)

        self.assertEqual(resposta.status_code, 409, resposta.data)
        self.assertEqual(resposta.data["codigo"], "falha_intermediaria")
        self.assertEqual(MovimentacaoGraos.objects.count(), 0)
        self.assertEqual(saldo_lote(self.lote_graos), Decimal("0"))
        self.assertFalse(
            lote.linhas.filter(movimentacao_graos__isnull=False).exists()
        )
        lote.refresh_from_db()
        self.assertEqual(lote.status, LoteImportacao.Status.FALHOU)
        auditoria = ConfirmacaoImportacao.objects.get()
        self.assertEqual(auditoria.status, ConfirmacaoImportacao.Status.FALHOU)

    def test_openapi_documenta_endpoint_de_confirmacao(self):
        resposta = self.client.get("/api/schema.json")
        self.assertEqual(resposta.status_code, 200)
        self.assertIn(
            "/importacoes/lotes/{id}/confirmar/",
            resposta.data["paths"],
        )

    def test_armazenagem_externa_preserva_propriedade_produtora(self):
        self.armazem.propriedade = None
        self.armazem.save()
        lote = self.criar_lote_confirmavel()
        resposta = self.confirmar(lote)
        self.assertEqual(resposta.status_code, 201, resposta.data)
        movimento = MovimentacaoGraos.objects.get()
        self.assertEqual(movimento.posicao.propriedade_id, self.propriedade.pk)
        self.assertEqual(movimento.posicao.cad_pro_id, self.lote_graos.cad_pro_id)

    def test_preview_associa_produtora_com_armazenagem_externa(self):
        self.armazem.propriedade = None
        self.armazem.save()
        lote = processar_preview_planilha(arquivo=criar_planilha_teste(), usuario=self.usuario)
        linha = lote.linhas.get(planilha="1", linha_origem=7)
        self.assertEqual(linha.propriedade_id, self.propriedade.pk)
        self.assertEqual(linha.lote_graos_id, self.lote_graos.pk)
        self.assertFalse(MovimentacaoGraos.objects.exists())

    def test_rejeita_cadpro_divergente_sem_credito(self):
        lote = self.criar_lote_confirmavel([{"dados_normalizados": {"cadpro_numero": "99999999"}}])
        resposta = self.confirmar(lote)
        self.assertEqual(resposta.status_code, 409, resposta.data)
        self.assertIn("CAD/PRO diverge", str(resposta.data))
        self.assertFalse(MovimentacaoGraos.objects.exists())

    def test_rejeita_vinculo_inativo_sem_credito(self):
        CADProPropriedade.objects.filter(propriedade=self.propriedade).update(ativo=False)
        resposta = self.confirmar(self.criar_lote_confirmavel())
        self.assertEqual(resposta.status_code, 409, resposta.data)
        self.assertFalse(MovimentacaoGraos.objects.exists())

    def test_rejeita_produtora_ausente_mesmo_com_armazem_da_propriedade(self):
        self.lote_graos.propriedade = None
        self.lote_graos.save()
        resposta = self.confirmar(self.criar_lote_confirmavel())
        self.assertEqual(resposta.status_code, 409, resposta.data)
        self.assertFalse(MovimentacaoGraos.objects.exists())

    def test_indica_permissao_para_interface(self):
        lote = self.criar_lote_confirmavel()
        self.assertTrue(self.client.get(f"/api/importacoes/lotes/{lote.pk}/").data["pode_confirmar"])
        outro = get_user_model().objects.create_user("consulta")
        self.client.force_authenticate(outro)
        self.assertFalse(self.client.get(f"/api/importacoes/lotes/{lote.pk}/").data["pode_confirmar"])

    def test_paginacao_da_interface_preserva_listagem_legada(self):
        lote = self.criar_lote_confirmavel([{} for _ in range(51)])
        legado = self.client.get("/api/importacoes/linhas/", {"lote": lote.pk})
        self.assertEqual(len(legado.data), 51)
        primeira = self.client.get("/api/importacoes/linhas/", {"lote": lote.pk, "page": 1})
        self.assertEqual(primeira.data["count"], 51)
        self.assertEqual(len(primeira.data["results"]), 50)
        self.assertIsNotNone(primeira.data["next"])
        segunda = self.client.get("/api/importacoes/linhas/", {"lote": lote.pk, "page": 2})
        self.assertEqual(len(segunda.data["results"]), 1)
        lotes = self.client.get("/api/importacoes/lotes/", {"page": 1})
        self.assertEqual(lotes.data["count"], 1)

    def test_banco_impede_hash_confirmado_repetido(self):
        from django.db import IntegrityError, transaction
        primeiro = self.criar_lote_confirmavel([{"hash_linha": "c" * 64}])
        segundo = self.criar_lote_confirmavel([{"hash_linha": "d" * 64}])
        self.assertEqual(self.confirmar(primeiro).status_code, 201)
        self.assertEqual(self.confirmar(segundo, key="segunda-confirmacao").status_code, 201)
        with self.assertRaises(IntegrityError), transaction.atomic():
            segundo.linhas.update(hash_linha="c" * 64)
        self.assertEqual(MovimentacaoGraos.objects.count(), 2)

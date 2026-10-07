from datetime import timedelta
from decimal import Decimal
from uuid import uuid4
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from apps.accounts.models import AcessoUsuario
from .test_cargas_colhidas import CargaColhidaBase
from .cargas_services import registrar_carga_colhida
from .models import ConferenciaEstoque, EntradaProducaoTerceiro, MovimentacaoGraos, TerceiroCadastro


class ExtratoContagemTests(CargaColhidaBase, APITestCase):
    def setUp(self):
        self.criar_contexto()
        self.client.force_authenticate(self.usuario)
        self.dados = {"depositante": "Terceiro", "cultura": "Soja", "safra": self.grupo.safra, "armazem": self.armazem.pk, "peso_total_kg": "1500", "tara_kg": "500", "peso_bruto_kg": "1000", "umidade_percentual": "13", "impureza_percentual": "1", "defeitos_percentual": "1", "data_entrada": "2026-10-01", "placa": "ABC1D23"}

    def entrada(self, **mudancas):
        r = self.client.post(reverse("terceiros-entradas"), {**self.dados, **mudancas}, format="json", HTTP_IDEMPOTENCY_KEY=str(uuid4()))
        self.assertEqual(r.status_code, 201, r.data)
        return r.data

    def operar(self, rota, pk, dados):
        r = self.client.post(reverse(rota, args=(pk,)), dados, format="json", HTTP_IDEMPOTENCY_KEY=str(uuid4()))
        self.assertEqual(r.status_code, 201, r.data)
        return r.data

    def test_extrato_correcao_saida_estorno_e_saldo_por_safra(self):
        self.dados['terceiro']=TerceiroCadastro.objects.create(codigo='EXTRATO',nome='Terceiro').pk
        e = self.entrada()
        r = self.client.patch(reverse("terceiros-entrada-detalhe", args=(e["id"],)), {**self.dados, "peso_total_kg": "2500", "versao": e["versao"], "motivo": "Corrigir"}, format="json", HTTP_IDEMPOTENCY_KEY=str(uuid4()))
        self.assertEqual(r.status_code, 200, r.data)
        retirada = self.operar("terceiros-saida", e["id"], {"quantidade_kg": "100", "data_movimento": "2026-10-07", "destino": "Retirada"})
        m = next(m for m in retirada["movimentos"] if m["tipo"] == "saida")
        self.operar("terceiros-estorno", m["id"], {"data_movimento": "2026-10-07", "motivo": "Desfazer"})
        self.entrada(safra="2025")
        r = self.client.get(reverse("terceiros-extrato"), {"depositante": "TERCEIRO", "safra": self.grupo.safra})
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["total"], 4)
        self.assertEqual(Decimal(r.data["itens"][-1]["saldo_acumulado_kg"]), Decimal(1960))
        self.assertEqual([i["id"] for i in r.data["itens"]], [i["id"] for i in sorted(r.data["itens"], key=lambda i:(str(i["data"]), i["id"]))])
        todos = self.client.get(reverse("terceiros-extrato"), {"depositante": "Terceiro"}).data["itens"]
        self.assertEqual(Decimal(next(i for i in todos if i["safra"] == "2025")["saldo_acumulado_kg"]), Decimal(980))

    def test_paginacao_extrato_preserva_baseline_e_valida_filtros(self):
        self.dados['terceiro']=TerceiroCadastro.objects.create(codigo='PAGINA',nome='Terceiro').pk
        for _ in range(26):
            self.entrada()
        r = self.client.get(reverse("terceiros-extrato"), {"depositante": "Terceiro", "pagina": 2})
        self.assertEqual(r.data["total"], 26)
        self.assertEqual(len(r.data["itens"]), 1)
        self.assertEqual(Decimal(r.data["itens"][0]["saldo_acumulado_kg"]), Decimal(25480))
        self.assertEqual(self.client.get(reverse("terceiros-extrato"), {"depositante": "Terceiro", "pagina": 0}).status_code, 400)
        self.assertEqual(self.client.get(reverse("terceiros-extrato")).status_code, 400)

    def test_duplicidade_informativa_exclui_edicao_e_cancelados(self):
        entrada = self.entrada()
        url = reverse("conferencia-pesagem")
        dados = {**self.dados, "origem": "terceiro", "depositante": "TERCEIRO", "placa": "ABC-1D23"}
        self.assertEqual(self.client.post(url, dados, format="json").data["duplicados"], [entrada["id"]])
        self.assertEqual(self.client.post(url, {**dados, "excluir_id": entrada["id"]}, format="json").data["duplicados"], [])
        self.assertEqual(self.client.post(url, {**dados, "data_entrada": "2026-10-02"}, format="json").data["duplicados"], [])
        m = next(m for m in entrada["movimentos"] if m["tipo"] == "entrada")
        self.operar("terceiros-estorno", m["id"], {"data_movimento": "2026-10-07", "motivo": "Cancelar"})
        self.assertEqual(self.client.post(url, dados, format="json").data["duplicados"], [])
        self.assertEqual(EntradaProducaoTerceiro.objects.count(), 1)

    def contagem(self, **mudancas):
        return {"armazem": self.armazem.pk, "cultura": "Soja", "safra": self.grupo.safra, "data_contagem": str(timezone.localdate()), "contado_kg": "1900", "justificativa": "Conferência física com balança", "chave_idempotencia": str(uuid4()), **mudancas}

    def test_contagem_snapshot_ambos_saldos_imutavel_e_reenvio(self):
        self.entrada()
        carga = registrar_carga_colhida(usuario=self.usuario, **self.dados_carga())
        antes = MovimentacaoGraos.objects.count()
        d = self.contagem()
        previa = self.client.get(reverse("conferencia-estoque-previa"), {k:v for k,v in d.items() if k in ("armazem", "cultura", "safra", "contado_kg")})
        self.assertEqual(previa.status_code, 200, previa.data)
        self.assertEqual(ConferenciaEstoque.objects.count(), 0)
        url = reverse("conferencia-estoque")
        r = self.client.post(url, d, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(Decimal(r.data["saldo_registrado_kg"]), carga.peso_liquido_kg + Decimal(980))
        self.assertEqual(previa.data["diferenca_kg"], r.data["diferenca_kg"])
        self.assertEqual(Decimal(r.data["diferenca_kg"]), Decimal(1900)-carga.peso_liquido_kg-Decimal(980))
        self.assertEqual(self.client.post(url, d, format="json").data["id"], r.data["id"])
        self.assertEqual(self.client.post(url, {**d, "contado_kg": "1800"}, format="json").status_code, 400)
        self.assertEqual(ConferenciaEstoque.objects.count(), 1)
        self.assertEqual(MovimentacaoGraos.objects.count(), antes)
        self.assertEqual(self.client.get(url).data[0]["responsavel"], self.usuario.username)
        registro = ConferenciaEstoque.objects.get()
        with self.assertRaises(ValidationError):
            registro.save()
        with self.assertRaises(ValidationError):
            ConferenciaEstoque.objects.update(contado_kg=1)
        with self.assertRaises(ValidationError):
            ConferenciaEstoque.objects.all().delete()

    def test_contagem_invalida_nao_grava(self):
        for alteracao in ({"contado_kg": "-1"}, {"justificativa": " "}, {"data_contagem": str(timezone.localdate()+timedelta(days=1))}):
            self.assertEqual(self.client.post(reverse("conferencia-estoque"), self.contagem(**alteracao), format="json").status_code, 400)
        self.assertEqual(ConferenciaEstoque.objects.count(), 0)

    def test_permissoes_reais_consulta_nao_autoriza_registro(self):
        AcessoUsuario.objects.create(usuario=self.usuario, modulos=["cargas"], permissoes={"cargas": ["consultar"]})
        self.client.force_authenticate(user=None)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(self.usuario).access_token}")
        self.assertEqual(self.client.get(reverse("conferencia-estoque")).status_code, 200)
        self.assertEqual(self.client.post(reverse("conferencia-estoque"), self.contagem(), format="json").status_code, 403)
        self.assertEqual(self.client.get(reverse("terceiros-extrato"), {"depositante": "Terceiro"}).status_code, 200)
        self.assertEqual(self.client.get(reverse("backup-status")).status_code, 403)
        self.client.credentials()
        self.assertEqual(self.client.get(reverse("conferencia-estoque")).status_code, 401)

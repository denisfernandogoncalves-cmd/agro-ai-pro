from datetime import date
from decimal import Decimal
from uuid import uuid4
from rest_framework.test import APITestCase
from apps.accounts.models import AcessoUsuario
from .cargas_services import registrar_carga_colhida
from .test_cargas_colhidas import CargaColhidaBase


class ConsultaEntradasTests(CargaColhidaBase, APITestCase):
    url = "/api/graos/cargas-colhidas/romaneios/"

    def setUp(self):
        self.criar_contexto()
        self.propriedade.nome = "Fazenda São José"
        self.propriedade.save()
        self.cad_pro.codigo = "00123"
        self.cad_pro.save()
        self.client.force_authenticate(self.usuario)
        self.cargas = [registrar_carga_colhida(usuario=self.usuario, **{
            **self.dados_carga(), "data_colheita": date(2026, 10, dia), "placa": f"ABC1D2{dia}"}) for dia in (1, 2)]
        self.terceiros = []
        for dia in range(1, 8):
            resposta = self.client.post("/api/graos/terceiros/entradas/", {
                "depositante": "José Externo", "cultura": "Milho", "safra": "2026",
                "armazem": self.armazem.pk, "peso_bruto_kg": "100", "umidade_percentual": "14",
                "impureza_percentual": "0", "defeitos_percentual": "0", "data_entrada": f"2026-10-{dia:02}",
            }, format="json", HTTP_IDEMPOTENCY_KEY=str(uuid4()))
            self.assertEqual(resposta.status_code, 201, resposta.data)
            self.terceiros.append(resposta.data)
        cancelada = self.terceiros[-1]
        resposta = self.client.delete(f"/api/graos/terceiros/entradas/{cancelada['id']}/", {
            "versao": cancelada["versao"], "motivo": "Teste de histórico", "data_movimento": "2026-10-07",
        }, format="json", HTTP_IDEMPOTENCY_KEY=str(uuid4()))
        self.assertEqual(resposta.status_code, 200, resposta.data)

    def test_pagina_no_banco_e_total_de_toda_consulta(self):
        esperado = sum(c.peso_liquido_kg for c in self.cargas) + Decimal("600")
        primeira = self.client.get(self.url).data
        segunda = self.client.get(self.url, {"pagina": 2}).data
        self.assertEqual(primeira["total"], 8)
        self.assertEqual(len(primeira["itens"]), 5)
        self.assertEqual(len(segunda["itens"]), 3)
        self.assertEqual(Decimal(primeira["peso_ativo_kg"]), esperado)
        self.assertEqual(primeira["peso_ativo_kg"], segunda["peso_ativo_kg"])
        self.assertEqual((segunda["inicio"], segunda["fim"]), (6, 8))
        chaves = lambda r: {(i["origem"], i["registro"]["id"]) for i in r["itens"]}
        self.assertFalse(chaves(primeira) & chaves(segunda))
        self.assertEqual(self.client.get(self.url, {"pagina": 999}).data["pagina"], 2)
        self.assertIn("consultado_em", primeira)

    def test_filtros_busca_sem_acento_snapshot_e_codigo_exato(self):
        for params, quantidade in (({"busca": "sao jose"}, 2), ({"busca": "00123"}, 2),
                                   ({"busca": "#00123"}, 0), ({"origem": "terceiro", "busca": "jose"}, 6),
                                   ({"cultura": "Milho", "inicio": "2026-10-02", "fim": "2026-10-03"}, 2),
                                   ({"terceiro": "JOSÉ"}, 6), ({"origem": "propria", "terceiro": "José"}, 0)):
            with self.subTest(params=params):
                r = self.client.get(self.url, params)
                self.assertEqual(r.status_code, 200, r.data)
                self.assertEqual(r.data["total"], quantidade)
        self.propriedade.nome = "Nome atualizado depois da carga"
        self.propriedade.save()
        self.assertEqual(self.client.get(self.url, {"busca": "sao jose"}).data["total"], 2)

    def test_historico_nao_soma_cancelados_e_consulta_vazia(self):
        ativa = self.client.get(self.url).data
        historico = self.client.get(self.url, {"historico": "true"}).data
        self.assertEqual(historico["total"], 9)
        self.assertEqual(historico["peso_ativo_kg"], ativa["peso_ativo_kg"])
        vazio = self.client.get(self.url, {"busca": "inexistente"}).data
        self.assertEqual((vazio["total"], vazio["inicio"], vazio["fim"], vazio["itens"]), (0, 0, 0, []))
        self.assertEqual(Decimal(vazio["peso_ativo_kg"]), 0)

    def test_parametros_invalidos_e_acesso(self):
        for params in ({"inicio": "2026-10-05", "fim": "2026-10-01"}, {"inicio": "2026-02-30"},
                       {"pagina": "0"}, {"por_pagina": "1000"}, {"origem": "outra"}):
            self.assertEqual(self.client.get(self.url, params).status_code, 400)
        AcessoUsuario.objects.create(usuario=self.usuario, modulos=["vendas"])
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get(self.url).status_code, 401)

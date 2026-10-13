from copy import deepcopy
from unittest.mock import patch
from uuid import uuid4

from django.urls import path, include
from django.test import override_settings
from rest_framework.test import APITestCase

from apps.accounts.models import AcessoUsuario
from apps.graos.models import CargaColhida
from apps.graos.test_cargas_colhidas import CargaColhidaBase
from .models import ReciboSincronizacao
from .views import servidor_id

urlpatterns = [path("api/offline/", include("apps.offline.urls"))]


@override_settings(ROOT_URLCONF=__name__)
class SincronizacaoTests(CargaColhidaBase, APITestCase):
    def setUp(self):
        self.criar_contexto()
        self.usuario.is_staff = True
        self.usuario.save()
        self.client.force_authenticate(self.usuario)
        self.payload = {
            "servidor": servidor_id(), "usuario": self.usuario.pk, "operacao": str(uuid4()), "dispositivo": str(uuid4()),
            "dados": {"propriedade": self.propriedade.pk, "cad_pro": str(self.cad_pro.pk),
                      "cultura": "Soja", "safra": "2026/2027", "armazem": self.armazem.pk,
                      "data_colheita": "2026-10-09", "peso_bruto_kg": "1000", "placa": "ABC1D23",
                      "umidade_percentual": "13", "impureza_percentual": "1", "defeitos_percentual": "1"},
        }

    def enviar(self, dados=None):
        return self.client.post("/api/offline/cargas/", dados or self.payload, format="json")

    def test_reenvio_retorna_mesmo_recibo_sem_duplicar_carga(self):
        primeira = self.enviar()
        self.assertEqual(primeira.status_code, 200, primeira.data)
        segunda = self.enviar()
        self.assertEqual(segunda.data, primeira.data)
        self.assertEqual(CargaColhida.objects.count(), 1)
        self.assertEqual(ReciboSincronizacao.objects.count(), 1)
        self.assertEqual(primeira.data["registro"]["peso_liquido_kg"], "980.000")

    def test_mesma_operacao_com_outros_dados_exige_conferencia(self):
        self.assertEqual(self.enviar().status_code, 200)
        alterada = deepcopy(self.payload)
        alterada["dados"]["peso_bruto_kg"] = "2000"
        self.assertEqual(self.enviar(alterada).status_code, 409)
        self.assertEqual(CargaColhida.objects.count(), 1)

    def test_servidor_errado_e_identificador_invalido_nao_gravam(self):
        for campo, valor in (("servidor", "outro"), ("operacao", "invalido"), ("registro", True)):
            dados = deepcopy(self.payload)
            dados[campo] = valor
            self.assertEqual(self.enviar(dados).status_code, 400)
        self.assertEqual(CargaColhida.objects.count(), 0)

    def test_permissao_revogada_bloqueia_inclusive_reenvio(self):
        self.assertEqual(self.enviar().status_code, 200)
        self.usuario.is_staff = False
        self.usuario.save()
        AcessoUsuario.objects.create(usuario=self.usuario, modulos=["cargas"], permissoes={"cargas": ["consultar"]})
        self.assertEqual(self.enviar().status_code, 403)
        self.assertEqual(CargaColhida.objects.count(), 1)

    def test_falha_no_recibo_desfaz_carga_e_movimento(self):
        with patch.object(ReciboSincronizacao.objects, "create", side_effect=RuntimeError("Falha simulada")):
            with self.assertRaises(RuntimeError):
                self.enviar()
        self.assertEqual(CargaColhida.objects.count(), 0)
        self.assertEqual(ReciboSincronizacao.objects.count(), 0)

    def test_edicao_com_versao_antiga_nao_sobrescreve(self):
        original = self.enviar().data
        edicao = {**self.payload, "operacao": str(uuid4()), "registro": original["registro"]["id"],
                  "versao_original": "antiga", "dados": {"observacoes": "Nova observação"}}
        self.assertEqual(self.enviar(edicao).status_code, 409)
        self.assertEqual(CargaColhida.objects.count(), 1)

    def test_correcao_valida_e_reenvio_preservam_historico(self):
        original = self.enviar().data
        edicao = {**self.payload, "operacao": str(uuid4()), "registro": original["registro"]["id"],
                  "versao_original": original["versao"],
                  "dados": {"observacoes": "Conferida offline", "motivo_correcao": "Conferência de campo"}}
        resposta = self.enviar(edicao)
        self.assertEqual(resposta.status_code, 200, resposta.data)
        self.assertEqual(self.enviar(edicao).data, resposta.data)
        self.assertEqual(CargaColhida.objects.count(), 2)
        self.assertEqual(CargaColhida.objects.filter(status="ativa").count(), 1)

    def test_sem_login_nao_acessa_contexto_nem_fila(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/offline/contexto/").status_code, 401)
        self.assertEqual(self.enviar().status_code, 401)

    def test_troca_de_conta_nao_aplica_operacao_do_usuario_anterior(self):
        dados = deepcopy(self.payload)
        dados["usuario"] = self.usuario.pk + 1
        self.assertEqual(self.enviar(dados).status_code, 403)
        self.assertEqual(CargaColhida.objects.count(), 0)

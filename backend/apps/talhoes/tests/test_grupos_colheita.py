from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.cadpro.models import CADPro, CADProPropriedade
from apps.propriedades.models import Propriedade
from apps.graos.cargas_services import _aplicar_rateio_producao
from apps.talhoes.models import GrupoPropriedadesColheita


class GruposPropriedadesTests(APITestCase):
    url = "/api/talhoes/grupos-colheita/"

    def setUp(self):
        self.usuario = get_user_model().objects.create_user(username="grupos")
        self.client.force_authenticate(self.usuario)
        self.a = Propriedade.objects.create(nome="Electra", municipio="Teste", uf="PR", area_hectares=30)
        self.b = Propriedade.objects.create(nome="Bom Jesus", municipio="Teste", uf="PR", area_hectares=10)
        self.cad = CADPro.objects.create(codigo="123", descricao="Compartilhado")
        self.outro = CADPro.objects.create(codigo="456", descricao="Outro")
        self.va = CADProPropriedade.objects.create(propriedade=self.a, cad_pro=self.cad)
        self.vb = CADProPropriedade.objects.create(propriedade=self.b, cad_pro=self.cad)
        self.vc = CADProPropriedade.objects.create(propriedade=self.b, cad_pro=self.outro)

    def criar(self, vinculos=None):
        return self.client.post(self.url, {
            "nome": "Fazenda Electra", "vinculos": vinculos or [str(self.va.pk), str(self.vb.pk)],
        }, format="json")

    def test_compartilhado_e_diferente_preservam_propriedades(self):
        resposta = self.criar()
        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.assertEqual(len(resposta.data["membros"]), 2)
        self.assertEqual({m["cad_pro"] for m in resposta.data["membros"]}, {str(self.cad.pk)})
        alterada = self.client.patch(f'{self.url}{resposta.data["id"]}/', {
            "vinculos": [str(self.va.pk), str(self.vc.pk)],
        }, format="json")
        self.assertEqual(alterada.status_code, 200, alterada.data)
        self.assertEqual({m["cad_pro"] for m in alterada.data["membros"]}, {str(self.cad.pk), str(self.outro.pk)})
        self.assertEqual(Propriedade.objects.count(), 2)

    def test_rejeita_grupo_vazio_duplicatas_e_vinculos_inativos(self):
        for vinculos in ([], [str(self.vb.pk), str(self.vc.pk)], [str(self.va.pk)] * 2):
            resposta = self.client.post(self.url, {"nome": "Inválido", "vinculos": vinculos}, format="json")
            self.assertEqual(resposta.status_code, 400, resposta.data)
        self.vb.ativo = False
        self.vb.save()
        self.assertEqual(self.criar().status_code, 400)
        self.assertEqual(GrupoPropriedadesColheita.objects.count(), 0)

    def test_vinculo_desativado_aparece_como_indisponivel(self):
        self.assertEqual(self.criar().status_code, 201)
        self.cad.ativo = False
        self.cad.save()
        resposta = self.client.get(self.url)
        self.assertTrue(all(not m["disponivel"] for m in resposta.data[0]["membros"]))
        opcoes = self.client.get(f"{self.url}opcoes/")
        self.assertEqual([o["id"] for o in opcoes.data], [str(self.vc.pk)])

    def test_autenticacao_inativacao_e_sem_exclusao(self):
        resposta = self.criar()
        detalhe = f'{self.url}{resposta.data["id"]}/'
        self.assertEqual(self.client.patch(detalhe, {"ativo": False}, format="json").status_code, 200)
        self.assertEqual(self.client.delete(detalhe).status_code, 405)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(self.url).status_code, 401)
        self.assertEqual(self.client.get(f"{self.url}opcoes/").status_code, 401)
        self.assertEqual(self.criar().status_code, 401)

    def test_rateio_continua_proporcional_com_cadpro_compartilhado(self):
        resposta = self.criar()
        propriedades = {self.a.pk: self.a, self.b.pk: self.b}
        contexto = {"propriedades": [{
            "id": m["propriedade"], "nome": m["propriedade_nome"],
            "proprietario": "", "area_hectares": str(propriedades[m["propriedade"]].area_hectares),
            "cad_pro_id": m["cad_pro"], "cad_pro_numero": m["cad_pro_codigo"],
        } for m in resposta.data["membros"]]}
        _aplicar_rateio_producao(contexto, peso_liquido_kg=Decimal("600"), sacas_60kg=Decimal("10"))
        parcelas = {p["propriedade_id"]: Decimal(p["peso_liquido_kg"]) for p in contexto["rateio_producao"]}
        self.assertEqual(parcelas, {self.a.pk: Decimal("450"), self.b.pk: Decimal("150")})

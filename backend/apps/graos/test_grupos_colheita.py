from django.core.exceptions import ValidationError
from django.urls import reverse
from rest_framework.test import APITestCase

from .test_cargas_colhidas import CargaColhidaBase
from .cargas_services import registrar_carga_colhida
from .models import ArmazemGraos, CargaColhida, GrupoColheita


class GrupoColheitaApiTests(CargaColhidaBase, APITestCase):
    def setUp(self):
        self.criar_contexto()
        self.client.force_authenticate(self.usuario)
        self.url = reverse("grupos-colheita-list")

    def payload(self, **alteracoes):
        dados = {
            "propriedade": self.propriedade.pk,
            "cad_pro": str(self.cad_pro.pk),
            "armazem_padrao": self.armazem.pk,
            "nome": "Equipe Sul",
            "cultura": "Milho",
            "safra": "2026/2027",
            "tolerancia_umidade_percentual": "14.00",
            "desconto_umidade_por_ponto": "1.000",
            "tolerancia_impureza_percentual": "1.00",
            "desconto_impureza_por_ponto": "1.000",
            "tolerancia_defeitos_percentual": "2.00",
            "desconto_defeitos_por_ponto": "1.000",
        }
        dados.update(alteracoes)
        return dados

    def test_crud_sem_delete_filtros_e_inativacao(self):
        criacao = self.client.post(self.url, self.payload(), format="json")
        self.assertEqual(criacao.status_code, 201, criacao.data)
        grupo_id = criacao.data["id"]
        self.assertEqual(criacao.data["cad_pro"], str(self.cad_pro.pk))
        self.assertEqual(criacao.data["armazem_padrao"], self.armazem.pk)
        self.assertFalse(criacao.data["contexto_congelado"])

        edicao = self.client.patch(
            reverse("grupos-colheita-detail", args=(grupo_id,)),
            {"nome": "Equipe Sul Atualizada"},
            format="json",
        )
        self.assertEqual(edicao.status_code, 200, edicao.data)
        filtrada = self.client.get(
            self.url,
            {
                "search": "Atualizada",
                "propriedade": self.propriedade.pk,
                "cad_pro": str(self.cad_pro.pk),
                "cultura": "milho",
                "safra": "2026/2027",
                "ativo": "true",
                "armazem_padrao": self.armazem.pk,
            },
        )
        self.assertEqual(filtrada.status_code, 200)
        self.assertEqual([item["id"] for item in filtrada.data], [grupo_id])
        self.assertEqual(
            self.client.delete(reverse("grupos-colheita-detail", args=(grupo_id,))).status_code,
            405,
        )
        inativada = self.client.post(
            reverse("grupos-colheita-inativar", args=(grupo_id,)),
            {},
            format="json",
        )
        self.assertEqual(inativada.status_code, 200)
        self.assertFalse(inativada.data["ativo"])

    def test_exige_armazenagem_padrao_valida(self):
        sem_armazem = self.client.post(
            self.url,
            self.payload(armazem_padrao=None),
            format="json",
        )
        self.assertEqual(sem_armazem.status_code, 400)
        outra_propriedade = self.propriedade.__class__.objects.create(
            nome="Fazenda Externa",
            municipio="Sorriso",
            uf="MT",
            area_hectares="100",
        )
        outro_armazem = ArmazemGraos.objects.create(
            propriedade=outra_propriedade,
            nome="Silo Externo",
            capacidade_kg="1000",
        )
        invalida = self.client.post(
            self.url,
            self.payload(armazem_padrao=outro_armazem.pk),
            format="json",
        )
        self.assertEqual(invalida.status_code, 400)
        self.assertIn("armazem_padrao", invalida.data)

    def test_contexto_congela_apos_carga_e_nome_permanece_editavel(self):
        registrar_carga_colhida(usuario=self.usuario, **self.dados_carga())
        detalhe = reverse("grupos-colheita-detail", args=(self.grupo.pk,))
        bloqueada = self.client.patch(
            detalhe,
            {"cultura": "Milho"},
            format="json",
        )
        self.assertEqual(bloqueada.status_code, 400, bloqueada.data)
        self.assertTrue(GrupoColheita.objects.get(pk=self.grupo.pk).cargas.exists())
        permitida = self.client.patch(
            detalhe,
            {"nome": "Equipe Norte Renomeada"},
            format="json",
        )
        self.assertEqual(permitida.status_code, 200, permitida.data)
        self.assertTrue(permitida.data["contexto_congelado"])

        self.grupo.refresh_from_db()
        self.grupo.safra = "2027/2028"
        with self.assertRaises(ValidationError):
            self.grupo.save()

    def test_carga_usa_armazem_padrao_e_serializa_uuid(self):
        payload = self.dados_carga()
        payload.pop("armazem")
        carga = registrar_carga_colhida(usuario=self.usuario, **payload)
        self.assertEqual(carga.armazem, self.armazem)
        resposta = self.client.get(reverse("cargas-colhidas-detail", args=(carga.pk,)))
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.data["cad_pro"], str(self.cad_pro.pk))

    def test_carga_rejeita_grupo_inativo_e_cadpro_com_saldo_nao_inativa(self):
        registrar_carga_colhida(usuario=self.usuario, **self.dados_carga())
        resposta = self.client.post(
            f"/api/cadpros/{self.cad_pro.pk}/inativar/",
            {},
            format="json",
        )
        self.assertEqual(resposta.status_code, 409, resposta.data)
        self.cad_pro.refresh_from_db()
        self.assertTrue(self.cad_pro.ativo)

        self.grupo.ativo = False
        self.grupo.save()
        payload = self.dados_carga()
        payload["placa"] = "XYZ9A99"
        with self.assertRaisesMessage(ValueError, "inativo"):
            registrar_carga_colhida(usuario=self.usuario, **payload)
        self.assertEqual(CargaColhida.objects.count(), 1)

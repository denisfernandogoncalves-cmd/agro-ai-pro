from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.estoque.models import LocalEstoque
from apps.propriedades.models import AcessoPropriedade, Propriedade

from .grain_models import AcessoCadPro, CadPro, Cultura, Safra
from .joint_models import CargaLoteConjunto, LoteConjuntoProducao, ParticipanteLoteConjunto, SaldoLoteConjunto


@override_settings(PROPERTY_ACCESS_LEGACY_TEST_MODE=False)
class ConfirmacaoRateioManualPendenteTests(APITestCase):
    def test_confirma_saldo_conjunto_sem_inventar_rateio_manual(self):
        usuario = get_user_model().objects.create_user(username="gestor-manual", password="teste")
        propriedades = [
            Propriedade.objects.create(nome="Manual A", municipio="Ivaiporã", uf="PR", area_hectares="20"),
            Propriedade.objects.create(nome="Manual B", municipio="Arapuã", uf="PR", area_hectares="20"),
        ]
        cadpros = []
        for indice, propriedade in enumerate(propriedades, start=1):
            AcessoPropriedade.objects.create(
                propriedade=propriedade,
                usuario=usuario,
                papel=AcessoPropriedade.Papel.GESTOR,
            )
            cadpro = CadPro.objects.create(
                propriedade=propriedade,
                codigo=f"MAN-{indice}",
                titular=f"Titular {indice}",
            )
            AcessoCadPro.objects.create(cadpro=cadpro, usuario=usuario)
            cadpros.append(cadpro)
        cultura = Cultura.objects.create(nome="Milho conjunto manual", codigo="milho-conjunto-manual", peso_saca_kg="60")
        safra = Safra.objects.create(nome="2027 manual")
        local = LocalEstoque.objects.create(nome="Silo manual compartilhado")
        lote = LoteConjuntoProducao.objects.create(
            cultura=cultura,
            safra=safra,
            data_inicio_colheita="2026-07-25",
            local_armazenagem=local,
            modo_rateio=LoteConjuntoProducao.ModoRateio.MANUAL,
            criado_por=usuario,
        )
        for propriedade, cadpro in zip(propriedades, cadpros):
            ParticipanteLoteConjunto.objects.create(
                lote=lote,
                propriedade=propriedade,
                cadpro=cadpro,
                area_cadastrada_ha="10.0000",
                area_colhida_ha="10.0000",
            )
        CargaLoteConjunto.objects.create(
            lote=lote,
            local_armazenagem=local,
            peso_bruto_kg="13000.000",
            tara_kg="3000.000",
            peso_liquido_kg="10000.000",
            criado_por=usuario,
        )
        self.client.force_authenticate(usuario)
        resposta = self.client.post(f"/api/producao/lotes-conjuntos/{lote.pk}/confirmar/", {}, format="json")
        self.assertEqual(resposta.status_code, status.HTTP_200_OK, resposta.data)
        lote.refresh_from_db()
        self.assertEqual(lote.status, LoteConjuntoProducao.Status.CONFIRMADO)
        self.assertEqual(lote.modo_rateio, LoteConjuntoProducao.ModoRateio.MANUAL)
        self.assertEqual(SaldoLoteConjunto.objects.get(lote=lote).quantidade_kg, Decimal("10000.000"))
        self.assertFalse(lote.cadpros_participantes.exists())
        self.assertTrue(all(item.quantidade_rateada_kg is None for item in lote.participantes.all()))

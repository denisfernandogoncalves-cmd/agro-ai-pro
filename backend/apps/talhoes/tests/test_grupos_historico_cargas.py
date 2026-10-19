from copy import deepcopy
from decimal import Decimal

from rest_framework.test import APITestCase
from apps.graos.test_cargas_colhidas import CargaColhidaBase
from apps.graos.cargas_services import registrar_carga_colhida
from apps.graos.models import RateioCargaColhida, PosicaoSaldoGraos
from apps.cadpro.models import CADProPropriedade
from apps.talhoes.models import GrupoPropriedadesColheita


class HistoricoCargaAposExclusaoGrupoTests(CargaColhidaBase, APITestCase):
    def test_excluir_grupo_nao_muda_contexto_area_rateio_ou_saldo_da_carga(self):
        self.criar_contexto()
        self.client.force_authenticate(self.usuario)
        grupo = GrupoPropriedadesColheita.objects.create(nome='Seleção da fazenda')
        grupo.vinculos.add(CADProPropriedade.objects.get(propriedade=self.propriedade, cad_pro=self.cad_pro))
        carga = registrar_carga_colhida(usuario=self.usuario, **self.dados_carga())
        contexto = deepcopy(carga.contexto_colheita)
        rateios = list(RateioCargaColhida.objects.filter(carga=carga).values())
        saldos = list(PosicaoSaldoGraos.objects.values())
        resposta = self.client.delete(f'/api/talhoes/grupos-colheita/{grupo.pk}/')
        self.assertEqual(resposta.status_code, 204)
        self.propriedade.area_hectares = 2000
        self.propriedade.save()
        grupo.refresh_from_db()
        carga.refresh_from_db()
        self.assertEqual(Decimal(grupo.historico_area[0]['area_hectares']), Decimal('1000'))
        self.assertEqual(carga.contexto_colheita, contexto)
        self.assertEqual(list(RateioCargaColhida.objects.filter(carga=carga).values()), rateios)
        self.assertEqual(list(PosicaoSaldoGraos.objects.values()), saldos)

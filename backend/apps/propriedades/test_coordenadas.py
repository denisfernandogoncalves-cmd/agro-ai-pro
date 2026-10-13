from decimal import Decimal
from django.test import TestCase
from .models import Propriedade
from .serializers import PropriedadeSerializer


class CoordenadasGmsTests(TestCase):
    def dados(self, **extras):
        return {'nome':'Teste GMS','municipio':'Teste','area_hectares':'2.42','formato_coordenadas':'gms','latitude_gms':'24°18\'28,97"S','longitude_gms':'51°42\'47,98"O', **extras}

    def salvar(self, dados, instance=None):
        s = PropriedadeSerializer(instance=instance,data=dados,partial=instance is not None)
        self.assertTrue(s.is_valid(),s.errors)
        return s.save()

    def test_salva_gms_original_sem_conversao(self):
        p=self.salvar(self.dados())
        p.refresh_from_db()
        self.assertEqual(p.latitude_gms,'24°18\'28,97"S')
        self.assertIsNone(p.latitude)
        self.assertIsNone(p.longitude)

    def test_converte_somente_com_pedido_explicito(self):
        p=self.salvar(self.dados(converter_coordenadas=True))
        self.assertEqual(p.latitude,Decimal('-24.308047'))
        self.assertEqual(p.longitude,Decimal('-51.713328'))
        self.assertEqual(p.formato_coordenadas,'gms')
        self.assertEqual(p.latitude_gms,'24°18\'28,97"S')

    def test_edicao_gms_remove_posicao_decimal_antiga(self):
        p=self.salvar(self.dados(converter_coordenadas=True))
        p=self.salvar({'latitude_gms':'24°19\'00"S'},p)
        self.assertIsNone(p.latitude)
        self.assertIsNone(p.longitude)

    def test_edicao_de_nome_preserva_conversao_anterior(self):
        p=self.salvar(self.dados(converter_coordenadas=True))
        p=self.salvar({'nome':'Nome revisado'},p)
        self.assertEqual(p.latitude,Decimal('-24.308047'))

    def test_rejeita_gms_invalido_hemisferio_e_parcial(self):
        for lat,lon in [('24°60\'00"S','51°42\'00"O'),('90°00\'01"S','51°42\'00"O'),('24°18\'00"O','51°42\'00"O'),('24°18\'00"S',''),('24°18\'60"S','51°42\'00"O')]:
            s=PropriedadeSerializer(data=self.dados(latitude_gms=lat,longitude_gms=lon))
            self.assertFalse(s.is_valid(),(lat,lon))
        self.assertFalse(Propriedade.objects.exists())

    def test_zero_e_limites_validos(self):
        p=self.salvar(self.dados(latitude_gms='0°00\'00"N',longitude_gms='180°00\'00"E',converter_coordenadas=True))
        self.assertEqual(p.latitude,Decimal('0'))
        self.assertEqual(p.longitude,Decimal('180'))

from decimal import Decimal
from django.test import TestCase
from .models import Propriedade
from .serializers import PropriedadeSerializer


class CoordenadasGmsTests(TestCase):
    def test_area_preserva_quatro_casas_em_alqueires(self):
        p = self.salvar(self.dados(area_hectares='34.220010'))
        p.refresh_from_db()
        self.assertEqual(p.area_hectares / Decimal('2.42'), Decimal('14.1405'))
        p = self.salvar({'area_hectares': '0.000242'}, p)
        p.refresh_from_db()
        self.assertEqual(p.area_hectares / Decimal('2.42'), Decimal('0.0001'))
    def test_apelido_manual_editavel_e_pesquisavel(self):
        from rest_framework.test import APIRequestFactory, force_authenticate
        from django.contrib.auth import get_user_model
        from .views import PropriedadeViewSet
        p = self.salvar(self.dados(apelido='Sede Nova'))
        self.assertIn('Sede Nova', PropriedadeSerializer(p).data['apelidos'])
        request = APIRequestFactory().get('/api/propriedades/', {'search': 'Sede Nova'})
        force_authenticate(request, user=get_user_model().objects.create_user(username='apelido'))
        resposta = PropriedadeViewSet.as_view({'get': 'list'})(request)
        self.assertEqual([item['id'] for item in resposta.data], [p.pk])
        p = self.salvar({'apelido': ''}, p)
        self.assertEqual(p.apelido, '')
    def test_tipo_imovel_opcional_e_editavel(self):
        p = self.salvar(self.dados())
        self.assertEqual(p.tipo_imovel, '')
        for tipo in ('arrendado', 'proprio', ''):
            p = self.salvar({'tipo_imovel': tipo}, p)
            p.refresh_from_db()
            self.assertEqual(p.tipo_imovel, tipo)
        s = PropriedadeSerializer(p, data={'tipo_imovel': 'invalido'}, partial=True)
        self.assertFalse(s.is_valid())
    def test_padrao_gms_e_identificacao_livre_editavel(self):
        p = self.salvar({'nome': 'Nova', 'municipio': 'Teste', 'area_hectares': '2.42', 'cad_pro_identificacao': 'Principal'})
        self.assertEqual(p.formato_coordenadas, 'gms')
        p = self.salvar({'cad_pro_identificacao': 'Secundário - matrícula 2'}, p)
        p.refresh_from_db()
        self.assertEqual(PropriedadeSerializer(p).data['cad_pro_identificacao'], 'Secundário - matrícula 2')
        p = self.salvar({'cad_pro_identificacao': ''}, p)
        self.assertEqual(p.cad_pro_identificacao, '')

    def test_padrao_gms_preserva_decimal_de_integracoes(self):
        p = self.salvar({'nome': 'Integração', 'municipio': 'Teste', 'area_hectares': '2.42', 'latitude': '-24.308047', 'longitude': '-51.713328'})
        self.assertEqual(p.latitude, Decimal('-24.308047'))

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

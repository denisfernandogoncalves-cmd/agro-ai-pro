import uuid
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from apps.financeiro.models import ParceiroFinanceiro
from apps.propriedades.models import Propriedade
from .models import ProdutoEstoque


class CoordenadasFaturamentoTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(get_user_model().objects.create_user('coordenadas-faturamento'))
        fornecedor = ParceiroFinanceiro.objects.create(nome='Fornecedor teste', tipo='fornecedor')
        produto = ProdutoEstoque.objects.create(nome='Produto teste', categoria='insumo', unidade='l')
        self.propriedade = Propriedade.objects.create(nome='Fazenda GMS', proprietario='Produtor', municipio='Jardim Alegre', area_hectares='24.2', formato_coordenadas='gms', latitude_gms='24°18\'28,97"S', longitude_gms='51°42\'47,98"O')
        self.dados = {'id': str(uuid.uuid4()), 'fornecedor': fornecedor.pk, 'produto': produto.pk, 'data_envio': '2026-10-09', 'embalagem': 'Balde', 'conteudo_embalagem': '20', 'dosagem_alqueire': '2', 'itens': [{'propriedade': self.propriedade.pk, 'area_alqueires': '10', 'quantidade_embalagens': '1'}]}

    def test_previa_preserva_gms_sem_converter(self):
        resposta = self.client.post('/api/estoque/faturamentos/previa/', self.dados, format='json')
        self.assertEqual(resposta.status_code, 200, resposta.data)
        item = resposta.data['itens'][0]
        self.assertEqual(item['latitude_gms'], self.propriedade.latitude_gms)
        self.assertEqual(item['longitude_gms'], self.propriedade.longitude_gms)
        self.assertIsNone(item['latitude'])
        self.assertIsNone(item['longitude'])

    def test_historico_congela_coordenadas_e_pdf_funciona(self):
        resposta = self.client.post('/api/estoque/faturamentos/confirmar/', self.dados, format='json')
        self.assertEqual(resposta.status_code, 201, resposta.data)
        original = self.propriedade.latitude_gms
        self.propriedade.latitude_gms = '24°00\'00"S'
        self.propriedade.save()
        url = f"/api/estoque/faturamentos/{resposta.data['id']}/"
        self.assertEqual(self.client.get(url).data['resumo']['itens'][0]['latitude_gms'], original)
        pdf = self.client.get(url + 'pdf/')
        self.assertEqual(pdf.status_code, 200)
        self.assertTrue(pdf.content.startswith(b'%PDF'))

    def test_decimal_zero_preservado(self):
        self.propriedade.formato_coordenadas = 'decimal'
        self.propriedade.latitude = 0
        self.propriedade.longitude = 0
        self.propriedade.save()
        resposta = self.client.post('/api/estoque/faturamentos/previa/', self.dados, format='json')
        self.assertEqual(resposta.status_code, 200, resposta.data)
        self.assertEqual(resposta.data['itens'][0]['latitude'], '0.000000')
        self.assertEqual(resposta.data['itens'][0]['longitude'], '0.000000')

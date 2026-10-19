from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.accounts.models import AcessoUsuario
from apps.estoque.models import ProdutoEstoque
from apps.propriedades.models import Propriedade


class BuscaGeralTests(APITestCase):
    url = '/api/core/busca/'

    def setUp(self):
        self.user = get_user_model().objects.create_user(username='busca')
        self.client.force_authenticate(self.user)
        self.acesso = AcessoUsuario.objects.create(usuario=self.user, modulos=['propriedades'])
        self.propriedade = Propriedade.objects.create(nome='Fazenda teste 98273', municipio='Teste', area_hectares='24.20', cad_pro_identificacao='Secundário')
        ProdutoEstoque.objects.create(nome='Produto reservado', principios_ativos='Glifosato', categoria='herbicida', unidade='l')

    def test_texto_numero_e_identificacao(self):
        for termo in ('98273', 'Fazenda', 'Secundário', 'secundario'):
            r = self.client.get(self.url, {'q': termo})
            self.assertEqual(r.status_code, 200)
            self.assertTrue(any(item['id'] == str(self.propriedade.pk) for item in r.data['resultados']))

    def test_permissoes_e_principio_ativo(self):
        self.assertEqual(self.client.get(self.url, {'q': 'Glifosato'}).data['resultados'], [])
        self.acesso.modulos = ['cadastros-agricolas']
        self.acesso.save()
        r = self.client.get(self.url, {'q': 'Glifosato'})
        self.assertEqual(r.data['resultados'][0]['titulo'], 'Produto reservado')
        self.acesso.permissoes = {'cadastros-agricolas': ['editar']}
        self.acesso.save()
        self.assertEqual(self.client.get(self.url, {'q': 'Glifosato'}).data['resultados'], [])

    def test_limite_vazio_validacao_e_autenticacao(self):
        for indice in range(7):
            Propriedade.objects.create(nome=f'Limite {indice}', municipio='Teste', area_hectares=1)
        r = self.client.get(self.url, {'q': 'Limite'})
        self.assertEqual(len(r.data['resultados']), 5)
        self.assertTrue(r.data['limitado'])
        self.assertEqual(self.client.get(self.url, {'q': ''}).data['resultados'], [])
        self.assertEqual(self.client.get(self.url, {'q': 'a' * 101}).status_code, 400)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(self.url, {'q': 'Fazenda'}).status_code, 401)

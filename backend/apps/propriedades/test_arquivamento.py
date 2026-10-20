from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from apps.accounts.models import AcessoUsuario
from apps.accounts.access import acao_da_requisicao
from apps.cadpro.models import CADPro, CADProPropriedade
from apps.talhoes.models import Talhao
from .models import Propriedade


class ArquivamentoPropriedadeTests(APITestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user('arquivo-propriedade')
        self.client.force_authenticate(self.usuario)
        self.propriedade = Propriedade.objects.create(nome='Propriedade com histórico', municipio='Teste', area_hectares='10')
        self.talhao = Talhao.objects.create(propriedade=self.propriedade, nome='Talhão histórico', area_hectares='5')
        cad = CADPro.objects.create(codigo='ARQ123', descricao='Cadastro histórico')
        self.vinculo = CADProPropriedade.objects.create(propriedade=self.propriedade, cad_pro=cad)
        self.url = f'/api/propriedades/{self.propriedade.pk}/'

    def test_arquivar_retirar_da_lista_e_restaurar_sem_perder_vinculos(self):
        resposta = self.client.post(self.url + 'arquivar/')
        self.assertEqual(resposta.status_code, 200, resposta.data)
        instante = resposta.data['arquivada_em']
        self.assertTrue(instante)
        self.assertEqual(self.client.get('/api/propriedades/').data, [])
        self.assertEqual(len(self.client.get('/api/propriedades/', {'incluir_arquivadas':'true'}).data), 1)
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.assertTrue(Talhao.objects.filter(pk=self.talhao.pk, propriedade=self.propriedade).exists())
        self.assertTrue(CADProPropriedade.objects.filter(pk=self.vinculo.pk, propriedade=self.propriedade).exists())
        self.assertEqual(self.client.post(self.url + 'arquivar/').data['arquivada_em'], instante)
        restaurada = self.client.post(self.url + 'restaurar/')
        self.assertEqual(restaurada.status_code, 200, restaurada.data)
        self.assertIsNone(restaurada.data['arquivada_em'])
        self.assertEqual(len(self.client.get('/api/propriedades/').data), 1)
        self.assertIsNone(self.client.post(self.url + 'restaurar/').data['arquivada_em'])

    def test_exclusao_informa_vinculos_reais_e_mantem_protecao(self):
        resposta = self.client.delete(self.url)
        self.assertEqual(resposta.status_code, 409)
        self.assertIn('talhões', resposta.data['detail'])
        self.assertIn('vínculos CAD/PRO', resposta.data['detail'])
        self.assertIn('Arquivar', resposta.data['detail'])
        self.assertTrue(Propriedade.objects.filter(pk=self.propriedade.pk).exists())

    def test_apenas_cadastro_nao_autoriza_arquivamento_e_restauracao(self):
        acesso = AcessoUsuario.objects.create(usuario=self.usuario, modulos=['propriedades'], permissoes={'propriedades':['consultar','cadastrar']})
        self.assertEqual(self.client.post(self.url + 'arquivar/').status_code, 403)
        self.assertEqual(self.client.post(self.url + 'restaurar/').status_code, 403)
        acesso.permissoes = {'propriedades':['consultar','excluir']}
        acesso.save()
        self.assertEqual(self.client.post(self.url + 'arquivar/').status_code, 200)
        self.assertEqual(self.client.post(self.url + 'restaurar/').status_code, 403)
        acesso.permissoes = {'propriedades':['consultar','editar']}
        acesso.save()
        self.assertEqual(self.client.post(self.url + 'restaurar/').status_code, 200)
        self.assertEqual(acao_da_requisicao('propriedades/1/arquivar/', 'POST'), 'excluir')
        self.assertEqual(acao_da_requisicao('propriedades/1/restaurar/', 'POST'), 'editar')

    def test_campo_nao_pode_ser_preenchido_por_patch(self):
        resposta = self.client.patch(self.url, {'arquivada_em':'2026-10-19T12:00:00Z'}, format='json')
        self.assertEqual(resposta.status_code, 200, resposta.data)
        self.assertIsNone(resposta.data['arquivada_em'])

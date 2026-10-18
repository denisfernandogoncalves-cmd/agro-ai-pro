from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from .models import AcessoUsuario
from .access import MODULOS, modulos_do_usuario


class ModulosRetiradosTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('admin_retirada', is_staff=True)
        self.client.force_authenticate(self.user)

    def test_rotas_retiradas_mesmo_para_administrador(self):
        for rota in ('/api/clima/previsoes/', '/api/clima/satelite/', '/api/mercado/cotacoes/', '/api/mercado/referencias/'):
            self.assertEqual(self.client.get(rota).status_code, 404, rota)

    def test_catalogo_e_acessos_antigos_sem_alterar_dados(self):
        self.assertNotIn('clima', MODULOS)
        self.assertNotIn('mercado', MODULOS)
        operador = get_user_model().objects.create_user('operador_antigo')
        acesso = AcessoUsuario.objects.create(usuario=operador, modulos=['cargas', 'clima', 'mercado'])
        self.assertEqual(modulos_do_usuario(operador), ['cargas'])
        acesso.refresh_from_db()
        self.assertEqual(acesso.modulos, ['cargas', 'clima', 'mercado'])

    def test_relatorios_retirados_recusam_consulta(self):
        for secao in ('clima', 'mercado'):
            r = self.client.get('/api/relatorios/operacionais/', {'secao': secao})
            self.assertEqual(r.status_code, 400)

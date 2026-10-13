"""Testa em PostgreSQL com base exclusiva; nunca recria bases preexistentes."""
import os
import sys
import uuid
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings.base')
import django
django.setup()
from django.conf import settings
from django.db import connection
from django.test.runner import DiscoverRunner
from django.test import override_settings


def main():
    if connection.vendor != 'postgresql':
        raise RuntimeError('Este runner isolado exige PostgreSQL.')
    nome='test_agro_isolado_'+uuid.uuid4().hex
    with connection.cursor() as cursor:
        cursor.execute('SELECT 1 FROM pg_database WHERE datname=%s',[nome])
        if cursor.fetchone():
            raise RuntimeError('Base já existe: execução cancelada, sem recriação.')
    settings.DATABASES['default']['TEST']['NAME']=nome
    print('Base temporária exclusiva:',nome,flush=True)
    with override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache', 'LOCATION': nome}}, AUTH_LOGIN_RATE='10000/min', AUTH_ACCOUNT_RATE='10000/min', AUTH_REFRESH_RATE='10000/min'), TemporaryDirectory(prefix='agro-test-media-') as media:
        settings.MEDIA_ROOT=media
        class RunnerComCobertura(DiscoverRunner):
            def build_suite(self, *args, **kwargs):
                suite = super().build_suite(*args, **kwargs)
                if suite.countTestCases() == 0:
                    raise RuntimeError("Nenhum teste descoberto: validação cancelada.")
                return suite
        return RunnerComCobertura(verbosity=1,interactive=True).run_tests(sys.argv[1:] or ["apps"])


if __name__=='__main__':
    sys.exit(bool(main()))

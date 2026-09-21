import os
import subprocess
import sys
from unittest import TestCase
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured

from config.settings.environment import (
    database_from_environment,
    database_from_url,
    env_bool,
    env_list,
)


class EnvironmentSettingsTests(TestCase):
    def test_database_url_preserva_credenciais_codificadas_e_ssl(self):
        config = database_from_url(
            "postgresql://agro%40user:p%40ss@db.example.com:5432/agro%2Dhomolog"
            "?sslmode=require"
        )

        self.assertEqual(config["NAME"], "agro-homolog")
        self.assertEqual(config["USER"], "agro@user")
        self.assertEqual(config["PASSWORD"], "p@ss")
        self.assertEqual(config["OPTIONS"], {"sslmode": "require"})

    def test_database_url_invalida_falha_sem_expor_credenciais(self):
        with self.assertRaisesRegex(ImproperlyConfigured, "postgres://"):
            database_from_url("mysql://usuario:segredo@db/agro")

    def test_database_discreta_permanece_compativel_com_desenvolvimento(self):
        with patch.dict(
            os.environ,
            {
                "DATABASE_URL": "",
                "POSTGRES_DB": "agro_test",
                "POSTGRES_USER": "test_user",
                "POSTGRES_PASSWORD": "test_password",
                "POSTGRES_HOST": "postgres",
                "POSTGRES_PORT": "5433",
            },
        ):
            config = database_from_environment()

        self.assertEqual(config["NAME"], "agro_test")
        self.assertEqual(config["HOST"], "postgres")
        self.assertEqual(config["PORT"], "5433")

    def test_listas_e_booleanos_de_ambiente_sao_normalizados(self):
        with patch.dict(
            os.environ,
            {"ORIGENS_TESTE": " https://a.example , ,https://b.example ", "FLAG_TESTE": "yes"},
        ):
            self.assertEqual(
                env_list("ORIGENS_TESTE"),
                ["https://a.example", "https://b.example"],
            )
            self.assertTrue(env_bool("FLAG_TESTE"))

    def test_booleano_invalido_falha_explicitamente(self):
        with patch.dict(os.environ, {"FLAG_TESTE": "talvez"}):
            with self.assertRaisesRegex(ImproperlyConfigured, "FLAG_TESTE"):
                env_bool("FLAG_TESTE")


class ProductionSettingsProcessTests(TestCase):
    @staticmethod
    def _run_production_settings(**overrides):
        env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("R2_")
            and key
            not in {
                "DATABASE_URL",
                "DJANGO_ALLOWED_HOSTS",
                "DJANGO_ALLOW_EPHEMERAL_MEDIA",
                "DJANGO_CORS_ALLOWED_ORIGINS",
                "DJANGO_CSRF_TRUSTED_ORIGINS",
                "DJANGO_SECRET_KEY",
                "DJANGO_SETTINGS_MODULE",
            }
        }
        env.update(
            {
                "DATABASE_URL": "postgresql://agro:password@db.example.com/agro",
                "DJANGO_ALLOWED_HOSTS": "api.example.com",
                "DJANGO_ALLOW_EPHEMERAL_MEDIA": "true",
                "DJANGO_CORS_ALLOWED_ORIGINS": "https://ui.example.com",
                "DJANGO_SECRET_KEY": "homologacao-segura-com-mais-de-trinta-e-dois-caracteres",
                "DJANGO_SETTINGS_MODULE": "config.settings.production",
            }
        )
        env.update(overrides)
        return subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import django; django.setup(); "
                    "from django.conf import settings; from django.test import Client; "
                    "response = Client().get('/api/health/', secure=True, "
                    "HTTP_HOST='api.example.com', HTTP_ORIGIN='https://ui.example.com'); "
                    "print(settings.DATABASES['default']['OPTIONS']['sslmode']); "
                    "print(settings.SECURE_SSL_REDIRECT); "
                    "print(response.status_code); "
                    "print(response['Access-Control-Allow-Origin']); "
                    "print(response['X-Content-Type-Options'])"
                ),
            ],
            cwd=os.fspath(settings_base_dir()),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_producao_valida_carrega_com_ssl_e_midia_descartavel_explicita(self):
        result = self._run_production_settings()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.splitlines(),
            ["require", "True", "200", "https://ui.example.com", "nosniff"],
        )

    def test_producao_rejeita_secret_de_desenvolvimento(self):
        result = self._run_production_settings(
            DJANGO_SECRET_KEY="development-only-change-me-at-least-32-characters"
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DJANGO_SECRET_KEY", result.stderr)

    def test_producao_exige_decisao_explicita_sobre_persistencia_de_midia(self):
        result = self._run_production_settings(DJANGO_ALLOW_EPHEMERAL_MEDIA="")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DJANGO_ALLOW_EPHEMERAL_MEDIA", result.stderr)

    def test_producao_rejeita_conexao_de_banco_sem_tls(self):
        result = self._run_production_settings(
            DATABASE_URL="postgresql://agro:password@db.example.com/agro?sslmode=disable"
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("sslmode", result.stderr)


def settings_base_dir():
    return os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

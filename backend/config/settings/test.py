from .base import *  # noqa: F403


DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
MEDIA_ROOT = BASE_DIR / "test-media"  # noqa: F405

# A suíte histórica foi criada antes do controle multiusuário. Novos testes de
# autorização desativam este modo explicitamente com override_settings.
PROPERTY_ACCESS_LEGACY_TEST_MODE = True

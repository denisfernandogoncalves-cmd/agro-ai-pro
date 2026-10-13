"""Configuração isolada do instalador Windows de testes."""
from .base import *  # noqa: F403

DEBUG = False
BASE_DIR = Path(os.environ["AGRO_DESKTOP_RESOURCES"]) / "backend"
TEMPLATES[0]["DIRS"] = [str(BASE_DIR / "templates")]
SECRET_KEY = os.environ["AGRO_DESKTOP_SECRET"]
ALLOWED_HOSTS = os.environ["AGRO_DESKTOP_HOSTS"].split(",")
DATABASES["default"].update(  # noqa: F405
    NAME="agro_testes", USER="agro", PASSWORD=os.environ["AGRO_DESKTOP_DB_PASSWORD"],
    HOST="127.0.0.1", PORT=os.environ.get("AGRO_DESKTOP_DB_PORT", "18766"),
)
MEDIA_ROOT = Path(os.environ["AGRO_DESKTOP_DATA"]) / "uploads"
STATIC_ROOT = Path(os.environ["AGRO_DESKTOP_RESOURCES"]) / "static"
ROOT_URLCONF = "config.desktop_urls"
CORS_ALLOW_ALL_ORIGINS = False
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Habilitado somente nos pacotes de desenvolvimento da sincronização.
AGRO_OFFLINE_ENABLE = os.environ.get("AGRO_OFFLINE_ENABLE") == "1"
if AGRO_OFFLINE_ENABLE:
    INSTALLED_APPS = [*INSTALLED_APPS, "apps.offline"]

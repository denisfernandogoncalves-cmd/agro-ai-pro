import os

from django.core.exceptions import ImproperlyConfigured

from .base import *
from .environment import env_bool, env_list, required_env


DEBUG = False

SECRET_KEY = required_env("DJANGO_SECRET_KEY")
if SECRET_KEY == "development-only-change-me-at-least-32-characters" or len(SECRET_KEY) < 32:
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY deve ser exclusivo do ambiente e possuir ao menos 32 caracteres."
    )

required_env("DATABASE_URL")
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS")
if not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "DJANGO_ALLOWED_HOSTS deve listar hosts explícitos e não pode usar '*'."
    )

CORS_ALLOWED_ORIGINS = env_list("DJANGO_CORS_ALLOWED_ORIGINS")
if not CORS_ALLOWED_ORIGINS:
    raise ImproperlyConfigured(
        "DJANGO_CORS_ALLOWED_ORIGINS deve listar a origem HTTPS do frontend."
    )
if any(not origin.startswith("https://") for origin in CORS_ALLOWED_ORIGINS):
    raise ImproperlyConfigured(
        "Todas as origens de produção devem usar HTTPS."
    )
CORS_ALLOWED_ORIGIN_REGEXES = env_list("DJANGO_CORS_ALLOWED_ORIGIN_REGEXES")
CSRF_TRUSTED_ORIGINS = env_list(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    CORS_ALLOWED_ORIGINS,
)

DATABASES["default"].update(
    {
        "CONN_MAX_AGE": int(os.getenv("DJANGO_DB_CONN_MAX_AGE", "60")),
        "CONN_HEALTH_CHECKS": True,
    }
)
database_options = DATABASES["default"].setdefault("OPTIONS", {})
database_options.setdefault("sslmode", "require")
if database_options["sslmode"] not in {"require", "verify-ca", "verify-full"}:
    raise ImproperlyConfigured(
        "DATABASE_URL deve exigir TLS com sslmode=require, verify-ca ou verify-full."
    )

MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

r2_values = {
    "access_key": os.getenv("R2_ACCESS_KEY_ID", "").strip(),
    "secret_key": os.getenv("R2_SECRET_ACCESS_KEY", "").strip(),
    "bucket_name": os.getenv("R2_BUCKET_NAME", "").strip(),
    "endpoint_url": os.getenv("R2_ENDPOINT_URL", "").strip(),
}
if any(r2_values.values()) and not all(r2_values.values()):
    raise ImproperlyConfigured(
        "R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME e R2_ENDPOINT_URL "
        "devem ser configuradas em conjunto."
    )
if all(r2_values.values()):
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            **r2_values,
            "region_name": "auto",
            "default_acl": None,
            "file_overwrite": False,
            "querystring_auth": True,
        },
    }
elif not env_bool("DJANGO_ALLOW_EPHEMERAL_MEDIA", False):
    raise ImproperlyConfigured(
        "Configure o R2 para mídia persistente ou confirme mídia descartável com "
        "DJANGO_ALLOW_EPHEMERAL_MEDIA=true na homologação."
    )

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)
SECURE_HSTS_SECONDS = int(os.getenv("DJANGO_SECURE_HSTS_SECONDS", "3600"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = False
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

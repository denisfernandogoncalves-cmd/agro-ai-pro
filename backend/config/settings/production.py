from .base import *  # noqa: F403
from django.core.exceptions import ImproperlyConfigured

DEBUG = False
if len(SECRET_KEY) < 50 or len(set(SECRET_KEY)) < 5 or SECRET_KEY.startswith(("development-only", "django-insecure-")):
    raise ImproperlyConfigured("Defina DJANGO_SECRET_KEY forte para o perfil de produção.")
if not os.getenv("DJANGO_ALLOWED_HOSTS") or "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured("Defina DJANGO_ALLOWED_HOSTS com os domínios autorizados.")
if not os.getenv("DJANGO_CACHE_URL"):
    raise ImproperlyConfigured("Defina DJANGO_CACHE_URL para o cache compartilhado de autenticação.")
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = int(os.getenv("DJANGO_HSTS_SECONDS", "3600"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

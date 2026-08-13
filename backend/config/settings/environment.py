import os
from urllib.parse import parse_qsl, unquote, urlparse

from django.core.exceptions import ImproperlyConfigured


def env_list(name, default=()):
    raw_value = os.getenv(name)
    if raw_value is None:
        return list(default)
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def env_bool(name, default=False):
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ImproperlyConfigured(
        f"{name} deve usar true/false, 1/0, yes/no ou on/off."
    )


def required_env(name):
    value = os.getenv(name, "").strip()
    if not value:
        raise ImproperlyConfigured(
            f"A variável de ambiente obrigatória {name} não foi configurada."
        )
    return value


def database_from_url(value):
    try:
        parsed = urlparse(value)
        port = parsed.port or 5432
    except ValueError as exc:
        raise ImproperlyConfigured("DATABASE_URL possui porta inválida.") from exc

    if parsed.scheme not in {"postgres", "postgresql"}:
        raise ImproperlyConfigured(
            "DATABASE_URL deve usar o esquema postgres:// ou postgresql://."
        )
    database_name = unquote(parsed.path.lstrip("/"))
    if not all((parsed.hostname, parsed.username, database_name)):
        raise ImproperlyConfigured(
            "DATABASE_URL deve informar host, usuário e nome do banco."
        )

    options = {key: value for key, value in parse_qsl(parsed.query) if value}
    config = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": database_name,
        "USER": unquote(parsed.username),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname,
        "PORT": str(port),
    }
    if options:
        config["OPTIONS"] = options
    return config


def database_from_environment():
    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        return database_from_url(database_url)
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "agro_ai_pro"),
        "USER": os.getenv("POSTGRES_USER", "postgres"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "postgres"),
        "HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
    }

from django.apps import AppConfig


class ProducaoConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.producao"

    def ready(self):
        from . import grain_enterprise_admin  # noqa: F401

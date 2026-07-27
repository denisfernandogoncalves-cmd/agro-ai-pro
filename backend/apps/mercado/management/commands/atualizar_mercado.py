import time

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.mercado.enterprise_update import atualizar_mercado_pendente


class Command(BaseCommand):
    help = "Atualiza automaticamente as cotações Enterprise do módulo Mercado."

    def add_arguments(self, parser):
        parser.add_argument("--continuous", action="store_true")
        parser.add_argument(
            "--interval-seconds",
            type=int,
            default=getattr(settings, "MERCADO_UPDATE_INTERVAL_SECONDS", 300),
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=getattr(settings, "MERCADO_MAX_UPDATES_PER_CYCLE", 20),
        )

    def handle(self, *args, **options):
        if not getattr(settings, "MERCADO_AUTOMATIC_UPDATE_ENABLED", True):
            self.stdout.write(self.style.WARNING("Atualização automática de mercado desativada."))
            return
        intervalo = max(int(options["interval_seconds"]), 60)
        limite = max(int(options["limit"]), 1)
        while True:
            resultado = atualizar_mercado_pendente(limite=limite)
            self.stdout.write(
                "Mercado: "
                f"{resultado['atualizadas']} atualizado(s), "
                f"{resultado['ignoradas']} ignorado(s), "
                f"{resultado['erros']} erro(s)."
            )
            if not options["continuous"]:
                break
            time.sleep(intervalo)

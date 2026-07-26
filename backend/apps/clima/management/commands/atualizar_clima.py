import time

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import close_old_connections

from apps.clima.services import atualizar_clima_pendente


class Command(BaseCommand):
    help = "Atualiza automaticamente as previsões climáticas pendentes."

    def add_arguments(self, parser):
        parser.add_argument(
            "--continuous",
            action="store_true",
            help="Mantém o processo ativo e executa ciclos periódicos.",
        )
        parser.add_argument(
            "--interval-seconds",
            type=int,
            default=settings.CLIMA_UPDATE_INTERVAL_SECONDS,
            help="Intervalo entre ciclos no modo contínuo.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=settings.CLIMA_MAX_UPDATES_PER_CYCLE,
            help="Quantidade máxima de propriedades processadas por ciclo.",
        )

    def handle(self, *args, **options):
        if not settings.CLIMA_AUTOMATIC_UPDATE_ENABLED:
            self.stdout.write(self.style.WARNING("Atualização climática automática desativada."))
            return
        intervalo = max(60, options["interval_seconds"])
        while True:
            close_old_connections()
            resumo = atualizar_clima_pendente(limite=options["limit"])
            self.stdout.write(
                "Clima: "
                f"{resumo['atualizadas']} atualizada(s), "
                f"{resumo['ignoradas']} ignorada(s), "
                f"{resumo['erros']} erro(s)."
            )
            if not options["continuous"]:
                break
            time.sleep(intervalo)

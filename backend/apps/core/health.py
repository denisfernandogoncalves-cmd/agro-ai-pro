"""Disponibilidade real do banco, separada da verificação de processo."""
import logging

from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.cache import never_cache

logger = logging.getLogger(__name__)


@never_cache
def readiness_view(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        cache.get("agro:readiness")
    except Exception:
        logger.warning("Dependência indisponível na verificação de readiness")
        return JsonResponse({"status": "indisponivel"}, status=503)
    return JsonResponse({"status": "ok"})

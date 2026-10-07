"""Lê evidências privadas do backup completo; nunca executa restauração."""
import json
from pathlib import Path
from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.accounts.views import NoStoreResponseMixin


def situacao_backup(raiz=None, agora=None):
    raiz = Path(raiz or settings.BASE_DIR.parent / "backups")
    agora = agora or timezone.now()
    ultima = None
    try:
        pastas = raiz.glob("agro-ai-pro-*")
        for pasta in pastas:
            if pasta.is_symlink() or not pasta.is_dir():
                continue
            try:
                manifesto = json.loads((pasta / "manifesto.json").read_text(encoding="utf-8"))
                arquivos = manifesto["arquivos"]
                if not all(nome in arquivos and (pasta / nome).is_file() and not (pasta / nome).is_symlink() and (pasta / nome).stat().st_size == arquivos[nome]["bytes"] for nome in ("banco.dump", "codigo-atual.zip", "uploads.zip")):
                    continue
                for prova in pasta.glob("verificacao-restauracao-*.json"):
                    if prova.is_symlink():
                        continue
                    registro = json.loads(prova.read_text(encoding="utf-8"))
                    if not all(registro.get(campo) is True for campo in ("hashes", "zip_crc", "restauracao_isolada")):
                        continue
                    instante = parse_datetime(registro.get("data", ""))
                    criado = parse_datetime(manifesto.get("data", ""))
                    if criado and timezone.is_naive(criado) and instante and timezone.is_aware(instante):
                        criado = timezone.make_aware(criado, instante.tzinfo)
                    if criado and instante and timezone.is_aware(criado) and timezone.is_aware(instante) and criado <= instante <= agora and (ultima is None or criado > ultima[0]):
                        ultima = (criado, pasta.name, instante)
            except (OSError, ValueError, KeyError, TypeError):
                continue
    except OSError:
        pass
    if ultima is None:
        return {"situacao": "ausente", "verificado_em": None, "identificador": None, "limite_dias": 7}
    return {"situacao": "atrasado" if agora - ultima[0] > timedelta(days=7) else "em_dia", "backup_em": ultima[0].isoformat(), "verificado_em": ultima[2].isoformat(), "identificador": ultima[1], "limite_dias": 7}


class BackupStatusView(NoStoreResponseMixin, APIView):
    permission_classes = (IsAdminUser,)

    def get(self, request):
        return Response(situacao_backup())

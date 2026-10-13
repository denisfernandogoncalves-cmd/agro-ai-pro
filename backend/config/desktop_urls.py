"""Mesmas APIs, com a interface compilada servida na janela desktop."""
from pathlib import Path
import os

from django.conf import settings
from django.http import FileResponse, Http404
from django.urls import include, path, re_path
from django.views.static import serve

from .urls import urlpatterns as api_patterns


def frontend(request, resource=""):
    root = Path(os.environ["AGRO_DESKTOP_RESOURCES"]) / "frontend"
    target = (root / resource).resolve()
    if not target.is_relative_to(root.resolve()):
        raise Http404
    if not target.is_file():
        if Path(resource).suffix:
            raise Http404
        target = root / "index.html"
    return FileResponse(target.open("rb"))


# A rota home original é um healthcheck, substituído pela interface neste pacote.
offline_patterns = [path("api/offline/", include("apps.offline.urls"))] if getattr(settings, "AGRO_OFFLINE_ENABLE", False) else []
urlpatterns = [p for p in api_patterns if getattr(p, "name", None) != "home"] + offline_patterns + [
    re_path(r"^static/(?P<path>.*)$", serve, {"document_root": settings.STATIC_ROOT}),
    # KML e anexos mantêm os mesmos URLs gerados pelas APIs atuais.
    re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
    re_path(r"^(?P<resource>.*)$", frontend),
]

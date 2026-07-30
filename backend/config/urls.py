from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework.permissions import AllowAny

from apps.accounts.views import LoginView, RefreshView


schema_view = get_schema_view(
    openapi.Info(
        title="AGRO-AI-PRO API",
        default_version="v1",
        description="API da versão funcional 1.0 do AGRO-AI-PRO.",
    ),
    public=True,
    permission_classes=(AllowAny,),
)


def health_view(request):
    return JsonResponse({
        "status": "ok",
        "service": "backend"
    })


urlpatterns = [

    path(
        "dashboard/",
        include("apps.dashboard.urls")
    ),

    path(
        "",
        health_view,
        name="home"
    ),

    path(
        "admin/",
        admin.site.urls
    ),

    # Health
    path(
        "api/health/",
        health_view
    ),

    # Autenticação JWT
    path(
        "api/auth/token/",
        LoginView.as_view(),
        name="token_obtain_pair"
    ),

    path(
        "api/auth/token/refresh/",
        RefreshView.as_view(),
        name="token_refresh"
    ),

    path(
        "api/auth/",
        include("apps.accounts.urls")
    ),

    path(
        "api/schema.json",
        schema_view.without_ui(cache_timeout=0),
        name="schema-json",
    ),

    path(
        "api/swagger/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),

    path(
        "api/redoc/",
        schema_view.with_ui("redoc", cache_timeout=0),
        name="schema-redoc",
    ),

    # APIs dos módulos
    path(
        "api/core/",
        include("apps.core.urls")
    ),

    path(
        "api/financeiro/",
        include("apps.financeiro.urls")
    ),

    path(
        "api/estoque/",
        include("apps.estoque.urls")
    ),

    path(
        "api/producao/",
        include("apps.producao.urls")
    ),

    path(
        "api/maquinas/",
        include("apps.maquinas.urls")
    ),

    path(
        "api/mercado/",
        include("apps.mercado.urls")
    ),

    path(
        "api/propriedades/",
        include("apps.propriedades.urls")
    ),

    path(
        "api/talhoes/",
        include("apps.talhoes.urls")
    ),

    path(
        "api/clima/",
        include("apps.clima.urls")
    ),

    path(
        "api/relatorios/",
        include("apps.relatorios.urls")
    ),

    path(
        "api/ai/",
        include("apps.ai.urls")
    ),
]


# Servir arquivos enviados (KML, imagens, relatórios)
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )

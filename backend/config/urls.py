from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


def health_view(request):
    return JsonResponse({"status": "ok", "service": "backend"})


urlpatterns = [
    path("dashboard/", include("apps.dashboard.urls")),
    path("", health_view, name="home"),
    path("admin/", admin.site.urls),
    path("api/health/", health_view),
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/core/", include("apps.core.urls")),
    path("api/accounts/", include("apps.accounts.urls")),
    path("api/financeiro/", include("apps.financeiro.urls")),
    path("api/estoque/", include("apps.estoque.urls")),
    path("api/producao/", include("apps.producao.urls")),
    path("api/mercado/", include("apps.mercado.urls")),
    path("api/propriedades/", include("apps.propriedades.urls")),
    path("api/talhoes/", include("apps.talhoes.urls")),
    path("api/relatorios/", include("apps.relatorios.urls")),
    path("api/ai/", include("apps.ai.urls")),
]

from django.utils.cache import patch_cache_control, patch_vary_headers


PRIVATE_API_PREFIXES = (
    "/api/accounts/",
    "/api/ai/",
    "/api/clima/",
    "/api/estoque/",
    "/api/financeiro/",
    "/api/importacoes/",
    "/api/maquinas/",
    "/api/mercado/",
    "/api/producao/",
    "/api/propriedades/",
    "/api/relatorios/",
    "/api/talhoes/",
)


class PrivateApiCacheHeadersMiddleware:
    """Impede armazenamento de respostas das APIs privadas."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith(PRIVATE_API_PREFIXES):
            patch_cache_control(response, no_store=True, private=True)
            patch_vary_headers(response, ("Authorization",))
        return response

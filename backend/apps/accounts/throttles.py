"""Limites de autenticação sem armazenar nomes de usuário ou tokens no cache."""
import hashlib
import ipaddress

from django.conf import settings
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.exceptions import APIException


class AutenticacaoIndisponivel(APIException):
    status_code = 503
    default_detail = "Autenticação temporariamente indisponível."
    default_code = "autenticacao_indisponivel"


class AutenticacaoThrottle(SimpleRateThrottle):
    scope = "auth_origem"
    setting_name = "AUTH_LOGIN_RATE"

    def allow_request(self, request, view):
        try:
            return super().allow_request(request, view)
        except Exception as erro:
            raise AutenticacaoIndisponivel() from erro

    def get_rate(self):
        return getattr(settings, self.setting_name, "30/min")

    def origem(self, request):
        peer = request.META.get("REMOTE_ADDR", "")
        # Só o proxy explicitamente confiável pode informar o IP do navegador.
        trusted = getattr(settings, "AUTH_TRUSTED_PROXY_NETWORKS", ())
        try:
            proxy = any(ipaddress.ip_address(peer) in ipaddress.ip_network(net) for net in trusted)
        except ValueError:
            proxy = False
        return request.META.get("HTTP_X_REAL_IP", peer) if proxy else peer

    def get_cache_key(self, request, view):
        ident = hashlib.sha256(self.origem(request).encode()).hexdigest()
        return self.cache_format % {"scope": self.scope, "ident": ident}


class LoginContaThrottle(AutenticacaoThrottle):
    scope = "auth_conta"
    setting_name = "AUTH_ACCOUNT_RATE"

    def get_rate(self):
        return getattr(settings, self.setting_name, "10/min")

    def get_cache_key(self, request, view):
        nome = str(request.data.get("username", "")) if hasattr(request.data, "get") else ""
        ident = hashlib.sha256(nome.strip().casefold().encode()).hexdigest()
        return self.cache_format % {"scope": self.scope, "ident": ident}


class RefreshThrottle(AutenticacaoThrottle):
    scope = "auth_refresh"
    setting_name = "AUTH_REFRESH_RATE"

    def get_rate(self):
        return getattr(settings, self.setting_name, "120/min")

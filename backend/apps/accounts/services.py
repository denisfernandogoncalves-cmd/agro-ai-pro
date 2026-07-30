import logging

import jwt
from jwt import InvalidTokenError
from rest_framework_simplejwt.exceptions import ExpiredTokenError, TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken, UntypedToken


logger = logging.getLogger(__name__)


class RefreshTokenInvalido(Exception):
    """Erro externo seguro para refresh ausente de validade criptográfica."""


def _validar_payload_refresh(payload):
    if payload.get("token_type") != RefreshToken.token_type:
        raise RefreshTokenInvalido
    if not payload.get("jti") or "exp" not in payload:
        raise RefreshTokenInvalido


def _decodificar_expirado_com_assinatura(refresh):
    token_sem_verificacao = RefreshToken(refresh, verify=False)
    backend = token_sem_verificacao.get_token_backend()
    try:
        return jwt.decode(
            refresh,
            backend.get_verifying_key(refresh),
            algorithms=[backend.algorithm],
            audience=backend.audience,
            issuer=backend.issuer,
            leeway=backend.get_leeway(),
            options={
                "verify_aud": backend.audience is not None,
                "verify_exp": False,
                "verify_signature": True,
            },
        )
    except InvalidTokenError as exc:
        raise RefreshTokenInvalido from exc


def revogar_refresh_token(refresh):
    """Revoga um refresh oficial do Simple JWT sem expor seu conteúdo."""

    try:
        token_validado = UntypedToken(refresh)
    except ExpiredTokenError:
        try:
            payload = _decodificar_expirado_com_assinatura(refresh)
        except (TokenError, TypeError, ValueError) as exc:
            raise RefreshTokenInvalido from exc
        _validar_payload_refresh(payload)
        logger.info("Logout JWT processado: refresh expirado.")
        return
    except (TokenError, TypeError, ValueError) as exc:
        raise RefreshTokenInvalido from exc

    payload = token_validado.payload
    _validar_payload_refresh(payload)
    jti = payload["jti"]

    if BlacklistedToken.objects.filter(token__jti=jti).exists():
        logger.info("Logout JWT processado: refresh já revogado.")
        return

    try:
        RefreshToken(refresh).blacklist()
    except TokenError as exc:
        if BlacklistedToken.objects.filter(token__jti=jti).exists():
            logger.info("Logout JWT processado: refresh revogado concorrentemente.")
            return
        raise RefreshTokenInvalido from exc

    logger.info("Logout JWT processado: refresh revogado.")

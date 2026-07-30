from django.utils.cache import patch_cache_control, patch_vary_headers
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import (
    LoginRequestSerializer,
    LogoutSerializer,
    TokenPairResponseSerializer,
    TokenRefreshRequestSerializer,
)
from .services import RefreshTokenInvalido, revogar_refresh_token


class NoStoreResponseMixin:
    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        patch_cache_control(response, no_store=True, private=True)
        patch_vary_headers(response, ("Authorization",))
        return response


class LoginView(NoStoreResponseMixin, TokenObtainPairView):
    @swagger_auto_schema(
        operation_description=(
            "Autentica usuário ativo e emite access de 15 minutos e refresh "
            "de 7 dias."
        ),
        request_body=LoginRequestSerializer,
        responses={
            status.HTTP_200_OK: TokenPairResponseSerializer,
            status.HTTP_401_UNAUTHORIZED: "Credenciais inválidas ou usuário inativo.",
        },
        security=[],
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class RefreshView(NoStoreResponseMixin, TokenRefreshView):
    @swagger_auto_schema(
        operation_description=(
            "Emite novo access e novo refresh. O refresh apresentado é "
            "bloqueado e não pode ser reutilizado."
        ),
        request_body=TokenRefreshRequestSerializer,
        responses={
            status.HTTP_200_OK: TokenPairResponseSerializer,
            status.HTTP_401_UNAUTHORIZED: "Refresh inválido, expirado ou revogado.",
        },
        security=[],
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class LogoutView(NoStoreResponseMixin, APIView):
    authentication_classes = ()
    permission_classes = ()

    @swagger_auto_schema(
        operation_description=(
            "Revoga somente o refresh apresentado. Não exige access token. "
            "A operação é idempotente, não invalida access tokens já emitidos "
            "e o cliente deve remover tokens e dados privados localmente. "
            "Respostas usam Cache-Control: no-store, private."
        ),
        request_body=LogoutSerializer,
        responses={
            status.HTTP_204_NO_CONTENT: openapi.Response(
                "Refresh revogado, já revogado ou expirado validado.",
                headers={
                    "Cache-Control": {
                        "description": "Proíbe armazenamento da resposta.",
                        "type": "string",
                        "default": "no-store, private",
                    },
                    "Vary": {
                        "description": "Separa respostas por autorização.",
                        "type": "string",
                        "default": "Authorization",
                    },
                },
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                "Campo ausente, token malformado, assinatura inválida ou tipo incorreto."
            ),
        },
        security=[],
    )
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            revogar_refresh_token(serializer.validated_data["refresh"])
        except RefreshTokenInvalido as exc:
            raise ValidationError(
                {"refresh": ["Token refresh inválido."]}
            ) from exc
        return Response(status=status.HTTP_204_NO_CONTENT)

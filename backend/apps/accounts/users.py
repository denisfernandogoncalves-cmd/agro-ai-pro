import logging
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.contrib.auth.password_validation import (
    CommonPasswordValidator, MinimumLengthValidator,
    NumericPasswordValidator, UserAttributeSimilarityValidator, validate_password,
)
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import generics, permissions, serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied

from .views import NoStoreResponseMixin
from .models import AcessoUsuario
from .access import ACOES, MODULOS, modulos_do_usuario, permissoes_do_usuario

logger = logging.getLogger(__name__)


def validar_administrador_atual(request):
    # A autenticação pode ter ocorrido antes de uma exclusão concorrente.
    administrador = get_user_model().objects.select_for_update().filter(pk=request.user.pk).first()
    if administrador is None or not administrador.is_active or not administrador.is_staff:
        raise PermissionDenied("Sua conta não tem mais permissão para administrar usuários.")
    request.user = administrador


class UserSerializer(serializers.ModelSerializer):
    is_active = serializers.BooleanField(required=False, default=True)
    password = serializers.CharField(write_only=True, required=False, trim_whitespace=False, max_length=128)
    password_confirmation = serializers.CharField(write_only=True, required=False, trim_whitespace=False, max_length=128)
    modulos = serializers.ListField(child=serializers.ChoiceField(choices=list(MODULOS)), required=False)

    permissoes = serializers.DictField(child=serializers.ListField(child=serializers.ChoiceField(choices=ACOES)), required=False)

    class Meta:
        model = get_user_model()
        fields = ("id", "username", "first_name", "last_name", "email", "is_active", "is_staff", "password", "password_confirmation", "modulos", "permissoes")
        read_only_fields = ("id", "is_staff")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["modulos"] = modulos_do_usuario(instance)
        data["permissoes"] = permissoes_do_usuario(instance)
        return data

    def validate(self, attrs):
        password = attrs.get("password")
        confirmation = attrs.pop("password_confirmation", None)
        if not self.instance and not password:
            raise serializers.ValidationError({"password": "Informe a senha do novo usuário."})
        if password is not None or confirmation is not None:
            if not password or password != confirmation:
                raise serializers.ValidationError({"password_confirmation": "As senhas não coincidem."})
            user = get_user_model()(**{field: attrs.get(field, getattr(self.instance, field, "")) for field in ("username", "first_name", "last_name", "email")})
            try:
                validate_password(password, user, password_validators=[
                    MinimumLengthValidator(8), UserAttributeSimilarityValidator(),
                    CommonPasswordValidator(), NumericPasswordValidator(),
                ])
            except DjangoValidationError as exc:
                raise serializers.ValidationError({"password": exc.messages}) from exc
        if self.instance and self.instance.is_staff and "modulos" in attrs and set(attrs["modulos"]) != set(MODULOS):
            raise serializers.ValidationError({"modulos": "Administradores mantêm acesso a todos os módulos."})
        configuradas = attrs.get("permissoes")
        if configuradas is not None:
            modulos = attrs.get("modulos", modulos_do_usuario(self.instance) if self.instance else list(MODULOS))
            if set(configuradas) - set(modulos):
                raise serializers.ValidationError({"permissoes": "Configure ações somente para os módulos selecionados."})
            for acoes in configuradas.values():
                if acoes and "consultar" not in acoes:
                    raise serializers.ValidationError({"permissoes": "Para utilizar um módulo, autorize também consultar."})
            if self.instance and self.instance.is_staff and any(set(acoes) != set(ACOES) for acoes in configuradas.values()):
                raise serializers.ValidationError({"permissoes": "Administradores mantêm todas as ações."})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        validar_administrador_atual(self.context["request"])
        modulos = validated_data.pop("modulos", list(MODULOS))
        permissoes = validated_data.pop("permissoes", None)
        user = get_user_model().objects.create_user(**validated_data)
        AcessoUsuario.objects.create(usuario=user, modulos=list(dict.fromkeys(modulos)), permissoes=permissoes)
        logger.info("Usuário criado: administrador_id=%s usuario_id=%s", self.context["request"].user.pk, user.pk)
        return user

    def update(self, instance, validated_data):
        modulos = validated_data.pop("modulos", None)
        permissoes = validated_data.pop("permissoes", None)
        password = validated_data.pop("password", None)
        instance = super().update(instance, validated_data)
        if password:
            instance.set_password(password)
            instance.save(update_fields=["password"])
        if modulos is not None or permissoes is not None:
            defaults = {}
            if modulos is not None:
                defaults["modulos"] = list(dict.fromkeys(modulos))
            if permissoes is not None:
                defaults["permissoes"] = {modulo: list(dict.fromkeys(acoes)) for modulo, acoes in permissoes.items()}
            AcessoUsuario.objects.update_or_create(usuario=instance, defaults=defaults)
        logger.info("Usuário atualizado: administrador_id=%s usuario_id=%s", self.context["request"].user.pk, instance.pk)
        return instance


class UsersView(NoStoreResponseMixin, generics.ListCreateAPIView):
    permission_classes = (permissions.IsAdminUser,)
    serializer_class = UserSerializer
    queryset = get_user_model().objects.exclude(acesso_modulos__excluido_em__isnull=False).order_by("username")


class UserDetailView(NoStoreResponseMixin, generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (permissions.IsAdminUser,)
    serializer_class = UserSerializer
    queryset = UsersView.queryset
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def proteger(self, user, desativar):
        if user.is_superuser and not self.request.user.is_superuser:
            raise serializers.ValidationError("Somente um superadministrador pode alterar esta conta.")
        if desativar and user.pk == self.request.user.pk:
            raise serializers.ValidationError("Você não pode excluir ou desativar sua própria conta.")
        if desativar and user.is_staff and user.is_active and not get_user_model().objects.filter(is_staff=True, is_active=True).exclude(pk=user.pk).exists():
            raise serializers.ValidationError("É necessário manter pelo menos um administrador ativo.")

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        # Serializa alterações para preservar o último administrador ativo.
        list(get_user_model().objects.select_for_update().order_by("pk").values_list("pk", flat=True))
        validar_administrador_atual(request)
        user = self.get_object()
        serializer = self.get_serializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.proteger(user, serializer.validated_data.get("is_active") is False)
        serializer.save()
        return Response(serializer.data)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        list(get_user_model().objects.select_for_update().order_by("pk").values_list("pk", flat=True))
        validar_administrador_atual(request)
        user = self.get_object()
        self.proteger(user, True)
        user.is_active = False
        user.save(update_fields=["is_active"])
        AcessoUsuario.objects.update_or_create(usuario=user, defaults={"modulos": [], "excluido_em": timezone.now()})
        logger.info("Usuário excluído logicamente: administrador_id=%s usuario_id=%s", request.user.pk, user.pk)
        return Response(status=204)


class CurrentUserView(NoStoreResponseMixin, APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        return Response({"id": request.user.pk, "username": request.user.username, "is_staff": request.user.is_staff, "modulos": modulos_do_usuario(request.user), "permissoes": permissoes_do_usuario(request.user)})

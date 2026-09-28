from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import (
    CommonPasswordValidator, MinimumLengthValidator,
    NumericPasswordValidator, UserAttributeSimilarityValidator, validate_password,
)
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import generics, permissions, serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from .views import NoStoreResponseMixin


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)
    password_confirmation = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)

    class Meta:
        model = get_user_model()
        fields = ("id", "username", "first_name", "last_name", "email", "is_active", "is_staff", "password", "password_confirmation")
        read_only_fields = ("id", "is_active", "is_staff")

    def validate(self, attrs):
        confirmation = attrs.pop("password_confirmation")
        if attrs["password"] != confirmation:
            raise serializers.ValidationError({"password_confirmation": "As senhas não coincidem."})
        user = get_user_model()(**{key: value for key, value in attrs.items() if key != "password"})
        try:
            validate_password(attrs["password"], user, password_validators=[
                MinimumLengthValidator(8), UserAttributeSimilarityValidator(),
                CommonPasswordValidator(), NumericPasswordValidator(),
            ])
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": exc.messages}) from exc
        return attrs

    def create(self, validated_data):
        return get_user_model().objects.create_user(**validated_data)


class UsersView(NoStoreResponseMixin, generics.ListCreateAPIView):
    permission_classes = (permissions.IsAdminUser,)
    serializer_class = UserSerializer
    queryset = get_user_model().objects.order_by("username")


class CurrentUserView(NoStoreResponseMixin, APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        return Response({"username": request.user.username, "is_staff": request.user.is_staff})

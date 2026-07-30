from rest_framework import serializers


class LoginRequestSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(
        allow_blank=False,
        trim_whitespace=False,
        write_only=True,
        help_text="Refresh token JWT que será revogado.",
    )

    class Meta:
        swagger_schema_fields = {
            "example": {
                "refresh": "eyJhbGciOiJIUzI1NiJ9.exemplo_ficticio_truncado..."
            }
        }


class TokenRefreshRequestSerializer(serializers.Serializer):
    refresh = serializers.CharField(write_only=True)


class TokenPairResponseSerializer(serializers.Serializer):
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)

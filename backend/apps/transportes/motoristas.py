from django.db import transaction
from rest_framework import serializers, viewsets
from rest_framework.response import Response
from apps.core.correcoes import EdicaoVersionadaMixin, VersaoCorrecaoSerializer, versao_correcao
from .models import Motorista
from apps.accounts.access import verificar_acesso


class MotoristaSerializer(VersaoCorrecaoSerializer, serializers.ModelSerializer):
    class Meta:
        model = Motorista
        fields = "__all__"


class MotoristaViewSet(EdicaoVersionadaMixin, viewsets.ModelViewSet):
    queryset = Motorista.objects.all()
    serializer_class = MotoristaSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        motorista = self.get_queryset().select_for_update().get(pk=self.get_object().pk)
        original = request.data.get("versao_correcao_original")
        if not isinstance(original, str) or not original:
            raise serializers.ValidationError({"versao_correcao_original": "Atualize a lista antes de excluir."})
        if original != versao_correcao(motorista):
            return Response({"detail": "Motorista alterado. Atualize a lista antes de excluir."}, status=409)
        motorista.ativo = False
        motorista.save(update_fields=("ativo",))
        return Response(self.get_serializer(motorista).data)

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        verificar_acesso(request.user, request.path, request.method)

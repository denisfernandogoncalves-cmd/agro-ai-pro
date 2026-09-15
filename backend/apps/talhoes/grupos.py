from django.db import transaction
from rest_framework import mixins, serializers, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.cadpro.models import CADProPropriedade
from .models import GrupoPropriedadesColheita


class GrupoPropriedadesSerializer(serializers.ModelSerializer):
    vinculos = serializers.PrimaryKeyRelatedField(
        many=True, allow_empty=False,
        queryset=CADProPropriedade.objects.filter(ativo=True, cad_pro__ativo=True),
    )
    membros = serializers.SerializerMethodField()

    class Meta:
        model = GrupoPropriedadesColheita
        fields = ("id", "nome", "ativo", "vinculos", "membros")

    def get_membros(self, obj):
        return [{
            "propriedade": vinculo.propriedade_id,
            "propriedade_nome": vinculo.propriedade.nome,
            "cad_pro": str(vinculo.cad_pro_id),
            "cad_pro_codigo": vinculo.cad_pro.codigo,
            "disponivel": vinculo.ativo and vinculo.cad_pro.ativo,
        } for vinculo in obj.vinculos.all()]

    def validate_vinculos(self, vinculos):
        propriedades = [v.propriedade_id for v in vinculos]
        if len(propriedades) != len(set(propriedades)):
            raise serializers.ValidationError("Selecione apenas um CAD/PRO por propriedade.")
        return vinculos

    @transaction.atomic
    def create(self, validated_data):
        return super().create(validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):
        return super().update(instance, validated_data)


class GrupoPropriedadesViewSet(
    mixins.CreateModelMixin, mixins.ListModelMixin,
    mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet,
):
    queryset = GrupoPropriedadesColheita.objects.prefetch_related(
        "vinculos__propriedade", "vinculos__cad_pro",
    )
    serializer_class = GrupoPropriedadesSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = None
    http_method_names = ("get", "post", "patch", "head", "options")

    @action(detail=False, methods=["get"])
    def opcoes(self, request):
        vinculos = CADProPropriedade.objects.filter(
            ativo=True, cad_pro__ativo=True,
        ).select_related("cad_pro", "propriedade")
        return Response([{
            "id": str(v.pk), "propriedade": v.propriedade_id,
            "propriedade_nome": v.propriedade.nome,
            "cad_pro": str(v.cad_pro_id), "cad_pro_codigo": v.cad_pro.codigo,
        } for v in vinculos])

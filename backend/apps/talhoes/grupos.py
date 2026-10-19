from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from apps.accounts.access import pode
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
        fields = ("id", "nome", "ativo", "vinculos", "membros", "excluido_em", "historico_area")
        read_only_fields = ("excluido_em", "historico_area")

    def get_membros(self, obj):
        if obj.excluido_em:
            return [{**m, "disponivel": False} for m in obj.historico_area]
        return [{
            "propriedade": vinculo.propriedade_id,
            "propriedade_nome": vinculo.propriedade.nome,
            "cad_pro": str(vinculo.cad_pro_id),
            "cad_pro_codigo": vinculo.cad_pro.codigo,
            "area_hectares": str(vinculo.propriedade.area_hectares),
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
        instance = GrupoPropriedadesColheita.objects.select_for_update().get(pk=instance.pk)
        if instance.excluido_em:
            raise serializers.ValidationError("Grupo excluído: o histórico é somente para consulta.")
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
    http_method_names = ("get", "post", "patch", "delete", "head", "options")

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == 'list' and self.request.query_params.get('incluir_excluidos') != 'true':
            qs = qs.filter(excluido_em__isnull=True)
        return qs

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        if not pode(request.user, 'talhoes', 'excluir'):
            raise PermissionDenied("Seu usuário não pode excluir grupos de colheita.")
        grupo = self.get_queryset().select_for_update().get(pk=self.get_object().pk)
        if grupo.excluido_em is None:
            grupo.historico_area = self.get_serializer(grupo).data['membros']
            grupo.excluido_em = timezone.now()
            grupo.ativo = False
            grupo.save(update_fields=('historico_area', 'excluido_em', 'ativo', 'atualizado_em'))
        return Response(status=204)

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

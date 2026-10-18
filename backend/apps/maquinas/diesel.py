from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from apps.accounts.access import verificar_acesso

from rest_framework import filters, mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.edicao_concorrente import EdicaoConcorrenteMixin
from apps.core.pagination import PaginacaoOpcional
from apps.core.query_params import validar_filtros
from .models import CompraDiesel
from .diesel_financeiro import sincronizar_conta_diesel
from apps.core.dias_uteis import vencimento_dia_util


class CompraDieselSerializer(serializers.ModelSerializer):
    valor_total = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    vencimento = serializers.DateField(read_only=True, allow_null=True)

    class Meta:
        model = CompraDiesel
        fields = "__all__"
        read_only_fields = ("criado_em", "atualizado_em")

    def validate(self, attrs):
        data = attrs.get("data", getattr(self.instance, "data", None))
        prazo = attrs.get("prazo_dias", getattr(self.instance, "prazo_dias", None))
        if data is not None and prazo is not None:
            from datetime import timedelta
            try:
                vencimento_dia_util(data, prazo)
            except OverflowError:
                raise serializers.ValidationError({"prazo_dias": "O prazo excede o limite de datas."})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        compra = super().create(validated_data)
        sincronizar_conta_diesel(compra)
        return compra

    @transaction.atomic
    def update(self, instance, validated_data):
        compra = super().update(instance, validated_data)
        sincronizar_conta_diesel(compra)
        return compra


class CompraDieselViewSet(EdicaoConcorrenteMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    queryset = CompraDiesel.objects.all()
    serializer_class = CompraDieselSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = PaginacaoOpcional
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ("fornecedor", "produtor", "documento", "observacoes")
    ordering_fields = ("data", "tipo", "fornecedor", "produtor", "litros", "valor_unitario")

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        verificar_acesso(request.user, request.path, request.method)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        compra = self.get_object()
        versao = serializers.DateTimeField().run_validation(request.data.get('atualizado_em_original'))
        if versao != compra.atualizado_em:
            return Response({'detail': 'Compra alterada. Atualize a lista antes de excluir.'}, status=409)
        compra.excluido_em = timezone.now()
        compra.save(update_fields=('excluido_em', 'atualizado_em'))
        sincronizar_conta_diesel(compra)
        return Response(status=204)

    def get_queryset(self):
        params = self.request.query_params
        datas = validar_filtros(params, datas=("data_inicio", "data_fim"))
        qs = super().get_queryset().filter(excluido_em__isnull=True)
        if self.action == 'destroy':
            qs = qs.select_for_update()
        for campo, lookup in (("data_inicio", "data__gte"), ("data_fim", "data__lte")):
            if campo in datas:
                qs = qs.filter(**{lookup: datas[campo]})
        for campo in ("tipo", "pagamento"):
            valor = params.get(campo, "").strip()
            if valor:
                escolhas = dict(CompraDiesel._meta.get_field(campo).choices)
                if valor not in escolhas:
                    raise serializers.ValidationError({campo: "Filtro inválido."})
                qs = qs.filter(**{campo: valor})
        for campo in ("fornecedor", "produtor"):
            valor = params.get(campo, "").strip()
            if valor:
                qs = qs.filter(**{campo + "__icontains": valor})
        return qs

    @action(detail=False, methods=['get'], url_path='vencimento')
    def previa_vencimento(self, request):
        data = serializers.DateField().run_validation(request.query_params.get('data'))
        prazo = serializers.IntegerField(min_value=0, max_value=32767).run_validation(request.query_params.get('prazo_dias'))
        try:
            vencimento = vencimento_dia_util(data, prazo)
        except OverflowError:
            raise serializers.ValidationError({'prazo_dias': 'O prazo excede o limite de datas.'})
        return Response({'vencimento': vencimento})

    @action(detail=False, methods=["get"])
    def resumo(self, request):
        # Soma valores arredondados por compra, como nas notas individuais.
        registros = self.filter_queryset(self.get_queryset())
        litros = Decimal("0")
        valor = Decimal("0")
        quantidade = 0
        for compra in registros.iterator():
            quantidade += 1
            litros += compra.litros
            valor += compra.valor_total
        return Response({"compras": quantidade, "litros": str(litros), "valor_total": str(valor)})

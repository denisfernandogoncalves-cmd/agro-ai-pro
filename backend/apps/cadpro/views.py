from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import CADPro
from .selectors import selecionar_cadpros, selecionar_vinculos
from .serializers import CADProPropriedadeSerializer, CADProSerializer
from .services import inativar_cadpro


class CADProViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = selecionar_cadpros()
    serializer_class = CADProSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ("codigo", "codigo_normalizado", "descricao")
    ordering_fields = ("codigo", "descricao", "ativo", "criado_em")
    ordering = ("codigo_normalizado", "id")
    http_method_names = ("get", "post", "patch", "head", "options")

    def get_queryset(self):
        queryset = super().get_queryset()
        ativo = self.request.query_params.get("ativo", "").strip().lower()
        if ativo in {"true", "false"}:
            queryset = queryset.filter(ativo=ativo == "true")
        return queryset

    @action(detail=True, methods=("get", "post"), url_path="propriedades")
    def propriedades(self, request, pk=None):
        cad_pro = self.get_object()
        if request.method == "GET":
            serializer = CADProPropriedadeSerializer(
                selecionar_vinculos(cad_pro.pk),
                many=True,
                context={"cad_pro": cad_pro, "request": request},
            )
            return Response(serializer.data)

        serializer = CADProPropriedadeSerializer(
            data=request.data,
            context={"cad_pro": cad_pro, "request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=("post",))
    def inativar(self, request, pk=None):
        self.get_object()
        cad_pro = inativar_cadpro(pk)
        return Response(self.get_serializer(cad_pro).data)

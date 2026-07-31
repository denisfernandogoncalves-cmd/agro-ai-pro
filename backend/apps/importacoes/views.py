from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import LinhaImportacao, LoteImportacao
from .serializers import (
    LinhaImportacaoSerializer,
    LoteImportacaoSerializer,
    ResultadoPreviewSerializer,
    UploadPlanilhaSerializer,
)
from .services import (
    ArquivoImportacaoDuplicadoError,
    PlanilhaImportacaoError,
    processar_preview_planilha,
)


class LoteImportacaoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LoteImportacao.objects.select_related("criado_por")
    serializer_class = LoteImportacaoSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ("arquivo_nome", "arquivo_sha256")
    ordering_fields = (
        "criado_em",
        "arquivo_nome",
        "status",
        "total_linhas",
        "total_erros",
    )
    ordering = ("-criado_em", "-id")

    def get_queryset(self):
        queryset = super().get_queryset()
        status_parametro = self.request.query_params.get("status", "").strip()
        if status_parametro:
            queryset = queryset.filter(status=status_parametro)
        return queryset

    @swagger_auto_schema(
        method="post",
        operation_summary="Gerar preview auditável de uma planilha XLSX",
        operation_description=(
            "Valida e persiste um lote de staging. Não cria movimentações de "
            "grãos e não altera saldos."
        ),
        manual_parameters=[
            openapi.Parameter(
                "arquivo",
                openapi.IN_FORM,
                description="Planilha XLSX com até 10 MB",
                type=openapi.TYPE_FILE,
                required=True,
            ),
        ],
        responses={
            201: ResultadoPreviewSerializer,
            400: "Planilha inválida",
            409: "Arquivo já importado",
        },
    )
    @action(
        detail=False,
        methods=["post"],
        url_path="preview",
        parser_classes=[MultiPartParser, FormParser],
    )
    def preview(self, request):
        entrada = UploadPlanilhaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        try:
            lote = processar_preview_planilha(
                arquivo=entrada.validated_data["arquivo"],
                usuario=request.user,
            )
        except ArquivoImportacaoDuplicadoError as exc:
            return Response(
                {
                    "detail": str(exc),
                    "lote_existente": exc.lote.id,
                    "arquivo_sha256": exc.lote.arquivo_sha256,
                },
                status=status.HTTP_409_CONFLICT,
            )
        except PlanilhaImportacaoError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        limite = 100
        linhas = lote.linhas.select_related(
            "propriedade",
            "lote_graos",
        )[:limite]
        resposta = {
            "lote": LoteImportacaoSerializer(
                lote,
                context={"request": request},
            ).data,
            "linhas_preview": LinhaImportacaoSerializer(
                linhas,
                many=True,
            ).data,
            "preview_limitado": lote.total_linhas > limite,
        }
        return Response(resposta, status=status.HTTP_201_CREATED)


class LinhaImportacaoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LinhaImportacao.objects.select_related(
        "lote_importacao",
        "propriedade",
        "lote_graos",
    )
    serializer_class = LinhaImportacaoSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = (
        "planilha",
        "dados_normalizados",
        "dados_originais",
        "hash_linha",
    )
    ordering_fields = ("sequencia", "planilha", "linha_origem", "status", "tipo")
    ordering = ("sequencia", "id")

    def get_queryset(self):
        queryset = super().get_queryset()
        for parametro, campo in (
            ("lote", "lote_importacao_id"),
            ("status", "status"),
            ("tipo", "tipo"),
            ("planilha", "planilha"),
            ("propriedade", "propriedade_id"),
            ("lote_graos", "lote_graos_id"),
        ):
            valor = self.request.query_params.get(parametro, "").strip()
            if valor:
                queryset = queryset.filter(**{campo: valor})
        return queryset

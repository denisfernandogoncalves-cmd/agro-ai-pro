from apps.core.excel import consulta_consistente
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .confirmation_services import (
    ConfirmacaoImportacaoError,
    confirmar_lote_importacao,
)
from .models import LinhaImportacao, LoteImportacao
from .permissions import PodeConfirmarImportacao
from .serializers import (
    ConfirmarLoteImportacaoSerializer,
    LinhaImportacaoSerializer,
    LoteImportacaoSerializer,
    ResultadoConfirmacaoSerializer,
    ResultadoPreviewSerializer,
    UploadPlanilhaSerializer,
)
from .services import (
    ArquivoImportacaoDuplicadoError,
    PlanilhaImportacaoError,
    processar_preview_planilha,
)


class PaginacaoImportacao(PageNumberPagination):
    page_size = 50

    def paginate_queryset(self, queryset, request, view=None):
        # Preserva os clientes existentes; a interface solicita paginação via page.
        if "page" not in request.query_params:
            return None
        return super().paginate_queryset(queryset, request, view)


class LoteImportacaoViewSet(viewsets.ReadOnlyModelViewSet):
    pagination_class = PaginacaoImportacao
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

    @action(detail=True, methods=["get"], url_path="conferencia-excel")
    @consulta_consistente()
    def conferencia_excel(self, request, pk=None):
        from apps.accounts.access import pode
        from apps.core.excel import PlanilhaExportacao
        from django.utils import timezone
        from rest_framework.exceptions import PermissionDenied
        from rest_framework import serializers
        import json
        if not pode(request.user,"importacoes","consultar") or not pode(request.user,"importacoes","imprimir"):
            raise PermissionDenied()
        lote=self.get_object()
        filtro=request.query_params.get("status_linha","")
        if filtro and filtro not in LinhaImportacao.Status.values:
            raise serializers.ValidationError("Situação da linha inválida.")
        linhas=lote.linhas.order_by("sequencia","id")
        if filtro: linhas=linhas.filter(status=filtro)
        if linhas.count()>100000:
            raise serializers.ValidationError("Mais de 100.000 linhas; aplique um filtro de situação.")
        planilha=PlanilhaExportacao("Conferência da importação; exportação somente leitura, sem confirmar movimentações.")
        planilha.adicionar("Base",["Campo","Valor"],[("Arquivo",lote.arquivo_nome),("SHA-256",lote.arquivo_sha256),("Lote",str(lote.pk)),("Situação do lote",lote.status),("Filtro de linhas",filtro or "Todas"),("Gerado em",timezone.now().isoformat()),("Confirmação",str(lote.confirmado_em or "Não confirmado")),("Critério","Status da linha representa validação. A confirmação operacional depende da situação do lote; não atribuir sucesso isolado a linhas de lote não confirmado.")])
        planilha.adicionar("Linhas",["Planilha","Linha original","Tipo","Validação","Erros","Advertências","Dados originais","Dados normalizados"],([r.planilha,r.linha_origem,r.tipo,r.status,"; ".join(r.erros),"; ".join(r.advertencias),json.dumps(r.dados_originais,ensure_ascii=False),json.dumps(r.dados_normalizados,ensure_ascii=False)] for r in linhas.iterator(chunk_size=1000)))
        resposta=planilha.resposta("conferencia-importacao")
        resposta["Cache-Control"]="private, no-store"
        return resposta

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

    @swagger_auto_schema(
        method="post",
        operation_summary="Confirmar definitivamente um lote de importação",
        operation_description=(
            "Exige confirmação explícita e permissão específica. Valida todas "
            "as linhas antes de registrar movimentações pelo serviço oficial "
            "de grãos em uma única transação atômica."
        ),
        request_body=ConfirmarLoteImportacaoSerializer,
        responses={
            200: ResultadoConfirmacaoSerializer,
            201: ResultadoConfirmacaoSerializer,
            400: "Requisição inválida",
            403: "Usuário sem permissão",
            404: "Lote não encontrado",
            409: "Confirmação rejeitada ou revertida",
        },
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="confirmar",
        permission_classes=[IsAuthenticated, PodeConfirmarImportacao],
    )
    def confirmar(self, request, pk=None):
        lote = self.get_object()
        entrada = ConfirmarLoteImportacaoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        try:
            resultado, replay = confirmar_lote_importacao(
                lote_id=lote.id,
                usuario=request.user,
                idempotency_key=entrada.validated_data["idempotency_key"],
            )
        except ConfirmacaoImportacaoError as exc:
            return Response(
                {
                    "detail": str(exc),
                    "codigo": exc.codigo,
                    "linhas_rejeitadas": exc.detalhes,
                    "replay_idempotente": exc.replay_idempotente,
                },
                status=status.HTTP_409_CONFLICT,
            )
        return Response(
            resultado,
            status=(
                status.HTTP_200_OK
                if replay
                else status.HTTP_201_CREATED
            ),
        )


class LinhaImportacaoViewSet(viewsets.ReadOnlyModelViewSet):
    pagination_class = PaginacaoImportacao
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

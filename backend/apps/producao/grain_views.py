import json

from django.db import IntegrityError
from django.http import HttpResponse
from rest_framework import filters, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.access import (
    PAPEIS_ADMINISTRACAO,
    PAPEIS_GESTAO,
    PAPEIS_OPERACAO,
    exigir_acesso_propriedade,
)
from apps.core.viewsets import EscopoGlobalViewSetMixin, EscopoPropriedadeViewSetMixin

from .grain_access import cadpros_visiveis, exigir_acesso_cadpro, filtrar_queryset_por_cadpro
from .grain_imports import confirm_import, file_hash, preview_import, validate_upload
from .grain_models import (
    AcessoCadPro,
    AuditoriaProducao,
    CadPro,
    ContratoProducao,
    Cultura,
    EmbarqueProducao,
    ImportacaoPlanilha,
    Motorista,
    MovimentacaoGraos,
    RecebimentoProducao,
    Safra,
    SaldoGraos,
    Veiculo,
)
from .grain_reports import dashboard_data, export_csv, export_pdf, export_xlsx, production_queryset, report_rows
from .grain_serializers import (
    AcessoCadProSerializer,
    AuditoriaProducaoSerializer,
    CadProSerializer,
    ContratoProducaoSerializer,
    CulturaSerializer,
    EmbarqueProducaoSerializer,
    ImportacaoPlanilhaSerializer,
    MotoristaSerializer,
    MovimentacaoGraosSerializer,
    RecebimentoProducaoSerializer,
    SafraSerializer,
    SaldoGraosSerializer,
    VeiculoSerializer,
)
from .grain_services import (
    ProducaoError,
    confirmar_embarque,
    confirmar_recebimento,
    estornar_embarque,
    estornar_recebimento,
    registrar_movimentacao,
)


class CulturaViewSet(EscopoGlobalViewSetMixin, viewsets.ModelViewSet):
    queryset = Cultura.objects.all()
    serializer_class = CulturaSerializer
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    search_fields = ("nome", "codigo")
    ordering_fields = ("nome", "codigo", "criado_em")


class SafraViewSet(EscopoGlobalViewSetMixin, viewsets.ModelViewSet):
    queryset = Safra.objects.all()
    serializer_class = SafraSerializer
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    search_fields = ("nome",)
    ordering_fields = ("nome", "data_inicio", "data_fim")


class MotoristaViewSet(EscopoGlobalViewSetMixin, viewsets.ModelViewSet):
    queryset = Motorista.objects.select_related("terceiro")
    serializer_class = MotoristaSerializer
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    search_fields = ("nome", "documento", "telefone")
    ordering_fields = ("nome", "criado_em")


class VeiculoViewSet(EscopoGlobalViewSetMixin, viewsets.ModelViewSet):
    queryset = Veiculo.objects.select_related("motorista_padrao", "terceiro")
    serializer_class = VeiculoSerializer
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    search_fields = ("placa", "descricao", "motorista_padrao__nome")
    ordering_fields = ("placa", "tipo", "criado_em")


class CadProViewSet(EscopoPropriedadeViewSetMixin, viewsets.ModelViewSet):
    queryset = CadPro.objects.select_related("propriedade")
    serializer_class = CadProSerializer
    property_filter = "propriedade_id"
    property_path = "propriedade"
    write_roles = PAPEIS_GESTAO
    action_roles = {"destroy": PAPEIS_ADMINISTRACAO}
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    search_fields = ("codigo", "titular", "documento", "propriedade__nome")
    ordering_fields = ("codigo", "titular", "criado_em")

    def get_queryset(self):
        queryset = cadpros_visiveis(self.request.user)
        property_id = self.request.query_params.get("propriedade", "").strip()
        return queryset.filter(propriedade_id=property_id) if property_id else queryset

    def perform_create(self, serializer):
        property_obj = serializer.validated_data["propriedade"]
        exigir_acesso_propriedade(self.request.user, property_obj, papeis=PAPEIS_GESTAO)
        cadpro = serializer.save()
        AcessoCadPro.objects.get_or_create(cadpro=cadpro, usuario=self.request.user)

    def perform_update(self, serializer):
        cadpro = serializer.instance
        exigir_acesso_cadpro(self.request.user, cadpro, papeis=PAPEIS_GESTAO)
        serializer.save()


class AcessoCadProViewSet(EscopoPropriedadeViewSetMixin, viewsets.ModelViewSet):
    queryset = AcessoCadPro.objects.select_related("cadpro__propriedade", "usuario")
    serializer_class = AcessoCadProSerializer
    property_filter = "cadpro__propriedade_id"
    property_path = "cadpro.propriedade"
    property_input_path = "cadpro.propriedade"
    write_roles = PAPEIS_ADMINISTRACAO
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    search_fields = ("cadpro__codigo", "usuario__username", "cadpro__propriedade__nome")
    ordering_fields = ("cadpro__codigo", "usuario__username", "criado_em")

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_superuser:
            return queryset
        return queryset.filter(cadpro__in=cadpros_visiveis(self.request.user))


class CadProScopedViewSetMixin(EscopoPropriedadeViewSetMixin):
    cadpro_field = "cadpro"

    def get_queryset(self):
        queryset = super().get_queryset()
        return filtrar_queryset_por_cadpro(queryset, self.request.user, self.cadpro_field)

    def _cadpro_from_serializer(self, serializer):
        return serializer.validated_data.get(
            self.cadpro_field,
            getattr(serializer.instance, f"{self.cadpro_field}", None),
        )

    def perform_create(self, serializer):
        cadpro = self._cadpro_from_serializer(serializer)
        exigir_acesso_cadpro(
            self.request.user,
            cadpro,
            papeis=self.get_roles_for_action("create"),
        )
        serializer.save()

    def perform_update(self, serializer):
        cadpro = self._cadpro_from_serializer(serializer)
        exigir_acesso_cadpro(
            self.request.user,
            cadpro,
            papeis=self.get_roles_for_action(self.action),
        )
        serializer.save()


class ContratoProducaoViewSet(CadProScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = ContratoProducao.objects.select_related(
        "propriedade", "cadpro", "cultura", "safra", "comprador"
    ).prefetch_related("embarques")
    serializer_class = ContratoProducaoSerializer
    property_filter = "propriedade_id"
    property_path = "propriedade"
    property_input_path = "propriedade"
    write_roles = PAPEIS_GESTAO
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    search_fields = ("numero", "comprador__nome", "cadpro__codigo", "cultura__nome")
    ordering_fields = ("data_contrato", "data_limite", "numero", "quantidade_kg", "status")

    def get_queryset(self):
        queryset = super().get_queryset()
        for parameter, field in (
            ("propriedade", "propriedade_id"),
            ("cadpro", "cadpro_id"),
            ("cultura", "cultura_id"),
            ("safra", "safra_id"),
            ("comprador", "comprador_id"),
            ("status", "status"),
        ):
            value = self.request.query_params.get(parameter, "").strip()
            if value:
                queryset = queryset.filter(**{field: value})
        return queryset


class RecebimentoProducaoViewSet(CadProScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = RecebimentoProducao.objects.select_related(
        "propriedade",
        "cadpro",
        "talhao",
        "cultura",
        "safra",
        "local_armazenagem",
        "motorista",
        "veiculo",
        "movimentacao",
    )
    serializer_class = RecebimentoProducaoSerializer
    property_filter = "propriedade_id"
    property_path = "propriedade"
    property_input_path = "propriedade"
    write_roles = PAPEIS_OPERACAO
    action_roles = {"destroy": PAPEIS_GESTAO, "estornar": PAPEIS_GESTAO}
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    search_fields = ("romaneio", "motorista__nome", "placa_informada", "cadpro__codigo")
    ordering_fields = ("data", "peso_liquido_kg", "umidade_percentual", "status")

    def get_queryset(self):
        queryset = super().get_queryset()
        for parameter, field in (
            ("propriedade", "propriedade_id"),
            ("cadpro", "cadpro_id"),
            ("talhao", "talhao_id"),
            ("cultura", "cultura_id"),
            ("safra", "safra_id"),
            ("local", "local_armazenagem_id"),
            ("status", "status"),
        ):
            value = self.request.query_params.get(parameter, "").strip()
            if value:
                queryset = queryset.filter(**{field: value})
        return queryset

    def update(self, request, *args, **kwargs):
        if self.get_object().status != RecebimentoProducao.Status.RASCUNHO:
            return Response(
                {"detail": "Somente recebimentos em rascunho podem ser editados."},
                status=status.HTTP_409_CONFLICT,
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if self.get_object().status != RecebimentoProducao.Status.RASCUNHO:
            return Response(
                {"detail": "Somente recebimentos em rascunho podem ser excluídos."},
                status=status.HTTP_409_CONFLICT,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=("post",))
    def confirmar(self, request, pk=None):
        try:
            receipt = confirmar_recebimento(self.get_object(), usuario=request.user)
        except (ProducaoError, serializers.ValidationError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(self.get_serializer(receipt).data)

    @action(detail=True, methods=("post",))
    def estornar(self, request, pk=None):
        reason = str(request.data.get("motivo", "")).strip()
        if not reason:
            return Response({"motivo": ["Informe o motivo do estorno."]}, status=status.HTTP_400_BAD_REQUEST)
        exigir_acesso_cadpro(request.user, self.get_object().cadpro, papeis=PAPEIS_GESTAO)
        try:
            receipt = estornar_recebimento(self.get_object(), usuario=request.user, motivo=reason)
        except ProducaoError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(self.get_serializer(receipt).data)


class EmbarqueProducaoViewSet(CadProScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = EmbarqueProducao.objects.select_related(
        "propriedade",
        "cadpro",
        "cultura",
        "safra",
        "local_armazenagem",
        "comprador",
        "contrato",
        "motorista",
        "veiculo",
        "movimentacao",
        "lancamento_financeiro",
    )
    serializer_class = EmbarqueProducaoSerializer
    property_filter = "propriedade_id"
    property_path = "propriedade"
    property_input_path = "propriedade"
    write_roles = PAPEIS_OPERACAO
    action_roles = {"destroy": PAPEIS_GESTAO, "estornar": PAPEIS_GESTAO}
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    search_fields = ("romaneio", "nota_produtor", "nota_empresa", "comprador__nome", "placa_informada")
    ordering_fields = ("data", "quantidade_kg", "valor_total", "status")

    def get_queryset(self):
        queryset = super().get_queryset()
        for parameter, field in (
            ("propriedade", "propriedade_id"),
            ("cadpro", "cadpro_id"),
            ("cultura", "cultura_id"),
            ("safra", "safra_id"),
            ("comprador", "comprador_id"),
            ("contrato", "contrato_id"),
            ("local", "local_armazenagem_id"),
            ("status", "status"),
        ):
            value = self.request.query_params.get(parameter, "").strip()
            if value:
                queryset = queryset.filter(**{field: value})
        return queryset

    def update(self, request, *args, **kwargs):
        if self.get_object().status != EmbarqueProducao.Status.RASCUNHO:
            return Response(
                {"detail": "Somente embarques em rascunho podem ser editados."},
                status=status.HTTP_409_CONFLICT,
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if self.get_object().status != EmbarqueProducao.Status.RASCUNHO:
            return Response(
                {"detail": "Somente embarques em rascunho podem ser excluídos."},
                status=status.HTTP_409_CONFLICT,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=("post",))
    def confirmar(self, request, pk=None):
        try:
            shipment = confirmar_embarque(self.get_object(), usuario=request.user)
        except (ProducaoError, serializers.ValidationError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(self.get_serializer(shipment).data)

    @action(detail=True, methods=("post",))
    def estornar(self, request, pk=None):
        reason = str(request.data.get("motivo", "")).strip()
        if not reason:
            return Response({"motivo": ["Informe o motivo do estorno."]}, status=status.HTTP_400_BAD_REQUEST)
        exigir_acesso_cadpro(request.user, self.get_object().cadpro, papeis=PAPEIS_GESTAO)
        try:
            shipment = estornar_embarque(self.get_object(), usuario=request.user, motivo=reason)
        except ProducaoError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(self.get_serializer(shipment).data)


class MovimentacaoInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = MovimentacaoGraos
        fields = (
            "tipo",
            "propriedade",
            "cadpro",
            "talhao",
            "cultura",
            "safra",
            "local_origem",
            "local_destino",
            "quantidade_kg",
            "motivo",
        )


class MovimentacaoGraosViewSet(CadProScopedViewSetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = MovimentacaoGraos.objects.select_related(
        "propriedade",
        "cadpro",
        "talhao",
        "cultura",
        "safra",
        "local_origem",
        "local_destino",
        "criado_por",
        "estorno_de",
    )
    serializer_class = MovimentacaoGraosSerializer
    property_filter = "propriedade_id"
    property_path = "propriedade"
    write_roles = PAPEIS_OPERACAO
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    search_fields = ("motivo", "referencia_tipo", "cadpro__codigo", "cultura__nome")
    ordering_fields = ("criado_em", "quantidade_kg", "tipo")

    def get_serializer_class(self):
        return MovimentacaoInputSerializer if self.action == "create" else MovimentacaoGraosSerializer

    def create(self, request, *args, **kwargs):
        serializer = MovimentacaoInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        roles = PAPEIS_GESTAO if data["tipo"] in {
            MovimentacaoGraos.Tipo.AJUSTE_ENTRADA,
            MovimentacaoGraos.Tipo.AJUSTE_SAIDA,
        } else PAPEIS_OPERACAO
        exigir_acesso_cadpro(request.user, data["cadpro"], papeis=roles)
        try:
            movement = registrar_movimentacao(
                usuario=request.user,
                referencia_tipo="manual",
                **data,
            )
        except ProducaoError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(MovimentacaoGraosSerializer(movement).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=("post",))
    def estornar(self, request, pk=None):
        original = self.get_object()
        reason = str(request.data.get("motivo", "")).strip()
        if not reason:
            return Response({"motivo": ["Informe o motivo do estorno."]}, status=status.HTTP_400_BAD_REQUEST)
        exigir_acesso_cadpro(request.user, original.cadpro, papeis=PAPEIS_GESTAO)
        try:
            reversal = registrar_movimentacao(
                usuario=request.user,
                tipo=MovimentacaoGraos.Tipo.ESTORNO,
                propriedade=original.propriedade,
                cadpro=original.cadpro,
                talhao=original.talhao,
                cultura=original.cultura,
                safra=original.safra,
                quantidade_kg=original.quantidade_kg,
                local_origem=original.local_origem,
                local_destino=original.local_destino,
                referencia_tipo="estorno_manual",
                referencia_id=original.pk,
                motivo=reason,
                estorno_de=original,
            )
        except ProducaoError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(MovimentacaoGraosSerializer(reversal).data, status=status.HTTP_201_CREATED)


class SaldoGraosViewSet(CadProScopedViewSetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = SaldoGraos.objects.select_related(
        "propriedade", "cadpro", "talhao", "cultura", "safra", "local_armazenagem"
    )
    serializer_class = SaldoGraosSerializer
    property_filter = "propriedade_id"
    property_path = "propriedade"
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    search_fields = ("cadpro__codigo", "cultura__nome", "safra__nome", "local_armazenagem__nome")
    ordering_fields = ("quantidade_kg", "atualizado_em", "cultura__nome")

    def get_queryset(self):
        queryset = super().get_queryset()
        for parameter, field in (
            ("propriedade", "propriedade_id"),
            ("cadpro", "cadpro_id"),
            ("talhao", "talhao_id"),
            ("cultura", "cultura_id"),
            ("safra", "safra_id"),
            ("local", "local_armazenagem_id"),
        ):
            value = self.request.query_params.get(parameter, "").strip()
            if value:
                queryset = queryset.filter(**{field: value})
        return queryset


class AuditoriaProducaoViewSet(EscopoPropriedadeViewSetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = AuditoriaProducao.objects.select_related("propriedade", "usuario")
    serializer_class = AuditoriaProducaoSerializer
    property_filter = "propriedade_id"
    property_path = "propriedade"
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    search_fields = ("acao", "entidade", "usuario__username")
    ordering_fields = ("criado_em", "acao", "entidade")


class ImportacaoPlanilhaViewSet(CadProScopedViewSetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = ImportacaoPlanilha.objects.select_related("propriedade", "cadpro", "criado_por")
    serializer_class = ImportacaoPlanilhaSerializer
    property_filter = "propriedade_id"
    property_path = "propriedade"
    cadpro_field = "cadpro"

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_superuser:
            return queryset
        return queryset.filter(criado_por=self.request.user)

    def create(self, request, *args, **kwargs):
        uploaded = request.FILES.get("arquivo")
        if not uploaded:
            return Response({"arquivo": ["Envie uma planilha."]}, status=status.HTTP_400_BAD_REQUEST)
        try:
            validate_upload(uploaded)
            property_id = int(request.data.get("propriedade"))
            property_obj = cadpros_visiveis(request.user, property_id).first().propriedade
            exigir_acesso_propriedade(request.user, property_obj, papeis=PAPEIS_GESTAO)
            cadpro_id = request.data.get("cadpro") or None
            cadpro = cadpros_visiveis(request.user, property_id).filter(pk=cadpro_id).first() if cadpro_id else None
            if cadpro_id and not cadpro:
                return Response({"cadpro": ["CAD/PRO não autorizado."]}, status=status.HTTP_404_NOT_FOUND)
            import_type = request.data.get("tipo")
            if import_type not in ImportacaoPlanilha.Tipo.values:
                return Response({"tipo": ["Tipo de importação inválido."]}, status=status.HTTP_400_BAD_REQUEST)
            raw_mapping = request.data.get("mapeamento") or "{}"
            manual_mapping = json.loads(raw_mapping) if isinstance(raw_mapping, str) else raw_mapping
            preview = preview_import(uploaded, import_type, manual_mapping)
            digest = file_hash(uploaded)
            uploaded.seek(0)
            record = ImportacaoPlanilha.objects.create(
                tipo=import_type,
                propriedade=property_obj,
                cadpro=cadpro,
                arquivo=uploaded,
                nome_original=uploaded.name,
                hash_arquivo=digest,
                mapeamento=preview["mapping"],
                previa=preview["preview"],
                inconsistencias=preview["errors"],
                total_linhas=preview["total_rows"],
                status=(ImportacaoPlanilha.Status.VALIDADA if not preview["errors"] else ImportacaoPlanilha.Status.ENVIADA),
                criado_por=request.user,
            )
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except IntegrityError:
            return Response({"detail": "Esta planilha já foi enviada por este usuário para o mesmo tipo."}, status=status.HTTP_409_CONFLICT)
        return Response(self.get_serializer(record).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=("post",))
    def validar(self, request, pk=None):
        record = self.get_object()
        exigir_acesso_propriedade(request.user, record.propriedade, papeis=PAPEIS_GESTAO)
        mapping = request.data.get("mapeamento", record.mapeamento)
        try:
            preview = preview_import(record.arquivo, record.tipo, mapping)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        record.mapeamento = preview["mapping"]
        record.previa = preview["preview"]
        record.inconsistencias = preview["errors"]
        record.total_linhas = preview["total_rows"]
        record.status = ImportacaoPlanilha.Status.VALIDADA if not preview["errors"] else ImportacaoPlanilha.Status.ENVIADA
        record.save(update_fields=("mapeamento", "previa", "inconsistencias", "total_linhas", "status"))
        return Response(self.get_serializer(record).data)

    @action(detail=True, methods=("post",))
    def confirmar(self, request, pk=None):
        record = self.get_object()
        exigir_acesso_propriedade(request.user, record.propriedade, papeis=PAPEIS_GESTAO)
        try:
            imported = confirm_import(record, user=request.user)
        except (ValueError, PermissionError, ProducaoError) as exc:
            detail = exc.args[0] if exc.args else str(exc)
            return Response(detail if isinstance(detail, dict) else {"detail": str(detail)}, status=status.HTTP_409_CONFLICT)
        return Response(self.get_serializer(imported).data)


class ProducaoDashboardView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        return Response(dashboard_data(request.user, request.query_params))


class RelatorioProducaoView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        queryset = production_queryset(request.user, request.query_params)
        rows = list(report_rows(queryset))
        output_format = request.query_params.get("formato", "json").lower()
        if output_format == "csv":
            response = HttpResponse(export_csv(rows), content_type="text/csv; charset=utf-8")
            response["Content-Disposition"] = 'attachment; filename="producao.csv"'
            return response
        if output_format == "xlsx":
            response = HttpResponse(
                export_xlsx(rows),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            response["Content-Disposition"] = 'attachment; filename="producao.xlsx"'
            return response
        if output_format == "pdf":
            response = HttpResponse(export_pdf(rows), content_type="application/pdf")
            response["Content-Disposition"] = 'attachment; filename="producao.pdf"'
            return response
        if output_format != "json":
            return Response({"formato": ["Use json, csv, xlsx ou pdf."]}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"count": len(rows), "results": rows})

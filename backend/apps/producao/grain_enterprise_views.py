import json

from django.db import IntegrityError, transaction
from django.db.models import Q
from rest_framework import filters, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.access import (
    PAPEIS_GESTAO,
    PAPEIS_OPERACAO,
    propriedades_visiveis,
    exigir_acesso_propriedade,
)
from apps.core.viewsets import EscopoGlobalViewSetMixin, EscopoPropriedadeViewSetMixin

from .grain_access import cadpros_visiveis, exigir_acesso_cadpro, filtrar_queryset_por_cadpro
from .grain_enterprise_models import (
    ConfiguracaoCultura,
    DetalheLocalArmazenagem,
    NotaFiscalProducao,
    OrigemTerceiroRecebimento,
    TransferenciaGraos,
)
from .grain_enterprise_serializers import (
    ConfiguracaoCulturaSerializer,
    DetalheLocalArmazenagemSerializer,
    EmbarqueEnterpriseSerializer,
    NotaFiscalProducaoSerializer,
    OrigemTerceiroRecebimentoSerializer,
    RecebimentoEnterpriseSerializer,
    TransferenciaGraosSerializer,
)
from .grain_enterprise_services import (
    confirmar_embarque_seguro,
    confirmar_recebimento_seguro,
    confirmar_transferencia,
    estornar_embarque_seguro,
    estornar_recebimento_seguro,
    estornar_transferencia,
    registrar_auditoria_enterprise,
    registrar_movimentacao_segura,
)
from .grain_imports import file_hash, preview_import, validate_upload
from .grain_models import (
    AuditoriaProducao,
    ContratoProducao,
    EmbarqueProducao,
    ImportacaoPlanilha,
    MovimentacaoGraos,
    RecebimentoProducao,
)
from .grain_serializers import MovimentacaoGraosSerializer
from .grain_services import ProducaoError
from .grain_views import (
    AuditoriaProducaoViewSet,
    CadProViewSet,
    ContratoProducaoViewSet,
    EmbarqueProducaoViewSet,
    ImportacaoPlanilhaViewSet,
    MovimentacaoGraosViewSet,
    RecebimentoProducaoViewSet,
)


class CadProEnterpriseViewSet(CadProViewSet):
    @transaction.atomic
    def perform_create(self, serializer):
        super().perform_create(serializer)
        registrar_auditoria_enterprise(
            usuario=self.request.user,
            acao="cadpro_criado",
            objeto=serializer.instance,
            cadpro=serializer.instance,
        )

    @transaction.atomic
    def perform_update(self, serializer):
        anteriores = {
            "codigo": serializer.instance.codigo,
            "titular": serializer.instance.titular,
            "ativo": serializer.instance.ativo,
        }
        super().perform_update(serializer)
        registrar_auditoria_enterprise(
            usuario=self.request.user,
            acao="cadpro_atualizado",
            objeto=serializer.instance,
            cadpro=serializer.instance,
            anteriores=anteriores,
        )


class ContratoProducaoEnterpriseViewSet(ContratoProducaoViewSet):
    @transaction.atomic
    def perform_create(self, serializer):
        super().perform_create(serializer)
        registrar_auditoria_enterprise(
            usuario=self.request.user,
            acao="contrato_criado",
            objeto=serializer.instance,
            cadpro=serializer.instance.cadpro,
        )

    @transaction.atomic
    def perform_update(self, serializer):
        anteriores = {
            "numero": serializer.instance.numero,
            "quantidade_kg": str(serializer.instance.quantidade_kg),
            "preco_saca": str(serializer.instance.preco_saca),
            "status": serializer.instance.status,
        }
        super().perform_update(serializer)
        registrar_auditoria_enterprise(
            usuario=self.request.user,
            acao="contrato_atualizado",
            objeto=serializer.instance,
            cadpro=serializer.instance.cadpro,
            anteriores=anteriores,
        )


class RecebimentoProducaoEnterpriseViewSet(RecebimentoProducaoViewSet):
    serializer_class = RecebimentoEnterpriseSerializer
    action_roles = {
        "destroy": PAPEIS_GESTAO,
        "confirmar": PAPEIS_OPERACAO,
        "estornar": PAPEIS_GESTAO,
    }

    def get_queryset(self):
        return super().get_queryset().select_related("origem_terceiro__terceiro").prefetch_related("notas_fiscais")

    @transaction.atomic
    def perform_create(self, serializer):
        super().perform_create(serializer)
        registrar_auditoria_enterprise(
            usuario=self.request.user,
            acao="recebimento_criado",
            objeto=serializer.instance,
            cadpro=serializer.instance.cadpro,
        )

    @transaction.atomic
    def perform_update(self, serializer):
        anteriores = {
            "peso_bruto_kg": str(serializer.instance.peso_bruto_kg),
            "peso_liquido_kg": str(serializer.instance.peso_liquido_kg),
            "umidade_percentual": str(serializer.instance.umidade_percentual),
            "status": serializer.instance.status,
        }
        super().perform_update(serializer)
        registrar_auditoria_enterprise(
            usuario=self.request.user,
            acao="recebimento_atualizado",
            objeto=serializer.instance,
            cadpro=serializer.instance.cadpro,
            anteriores=anteriores,
        )

    @action(detail=True, methods=("post",))
    def confirmar(self, request, pk=None):
        try:
            receipt = confirmar_recebimento_seguro(self.get_object(), usuario=request.user)
        except (ProducaoError, serializers.ValidationError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(self.get_serializer(receipt).data)

    @action(detail=True, methods=("post",))
    def estornar(self, request, pk=None):
        reason = str(request.data.get("motivo", "")).strip()
        if not reason:
            return Response({"motivo": ["Informe o motivo do estorno."]}, status=status.HTTP_400_BAD_REQUEST)
        try:
            receipt = estornar_recebimento_seguro(
                self.get_object(),
                usuario=request.user,
                motivo=reason,
            )
        except ProducaoError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(self.get_serializer(receipt).data)


class EmbarqueProducaoEnterpriseViewSet(EmbarqueProducaoViewSet):
    serializer_class = EmbarqueEnterpriseSerializer
    write_roles = PAPEIS_GESTAO
    action_roles = {
        "destroy": PAPEIS_GESTAO,
        "confirmar": PAPEIS_GESTAO,
        "estornar": PAPEIS_GESTAO,
    }

    def get_queryset(self):
        return super().get_queryset().prefetch_related("notas_fiscais")

    @transaction.atomic
    def perform_create(self, serializer):
        super().perform_create(serializer)
        registrar_auditoria_enterprise(
            usuario=self.request.user,
            acao="embarque_criado",
            objeto=serializer.instance,
            cadpro=serializer.instance.cadpro,
        )

    @transaction.atomic
    def perform_update(self, serializer):
        anteriores = {
            "quantidade_kg": str(serializer.instance.quantidade_kg),
            "preco_saca": str(serializer.instance.preco_saca),
            "valor_total": str(serializer.instance.valor_total),
            "status": serializer.instance.status,
        }
        super().perform_update(serializer)
        registrar_auditoria_enterprise(
            usuario=self.request.user,
            acao="embarque_atualizado",
            objeto=serializer.instance,
            cadpro=serializer.instance.cadpro,
            anteriores=anteriores,
        )

    @action(detail=True, methods=("post",))
    def confirmar(self, request, pk=None):
        try:
            shipment = confirmar_embarque_seguro(self.get_object(), usuario=request.user)
        except (ProducaoError, serializers.ValidationError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(self.get_serializer(shipment).data)

    @action(detail=True, methods=("post",))
    def estornar(self, request, pk=None):
        reason = str(request.data.get("motivo", "")).strip()
        if not reason:
            return Response({"motivo": ["Informe o motivo do estorno."]}, status=status.HTTP_400_BAD_REQUEST)
        try:
            shipment = estornar_embarque_seguro(
                self.get_object(),
                usuario=request.user,
                motivo=reason,
            )
        except ProducaoError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(self.get_serializer(shipment).data)


class MovimentacaoGraosEnterpriseViewSet(MovimentacaoGraosViewSet):
    def create(self, request, *args, **kwargs):
        serializer_class = super().get_serializer_class()
        serializer = serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            movement = registrar_movimentacao_segura(
                usuario=request.user,
                referencia_tipo="manual",
                **data,
            )
        except ProducaoError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(
            MovimentacaoGraosSerializer(movement).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=("post",))
    def estornar(self, request, pk=None):
        original = self.get_object()
        reason = str(request.data.get("motivo", "")).strip()
        if not reason:
            return Response({"motivo": ["Informe o motivo do estorno."]}, status=status.HTTP_400_BAD_REQUEST)
        try:
            reversal = registrar_movimentacao_segura(
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
        return Response(
            MovimentacaoGraosSerializer(reversal).data,
            status=status.HTTP_201_CREATED,
        )


class TransferenciaGraosViewSet(viewsets.ModelViewSet):
    serializer_class = TransferenciaGraosSerializer
    permission_classes = RecebimentoProducaoEnterpriseViewSet.permission_classes
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    search_fields = (
        "cadpro_origem__codigo",
        "cadpro_destino__codigo",
        "cultura__nome",
        "safra__nome",
        "motivo",
    )
    ordering_fields = ("data", "quantidade_kg", "status")

    def get_queryset(self):
        queryset = TransferenciaGraos.objects.select_related(
            "propriedade_origem",
            "cadpro_origem",
            "talhao_origem",
            "local_origem",
            "propriedade_destino",
            "cadpro_destino",
            "talhao_destino",
            "local_destino",
            "cultura",
            "safra",
            "criado_por",
            "confirmado_por",
        )
        if self.request.user.is_superuser:
            return queryset
        visible = cadpros_visiveis(self.request.user).values_list("id", flat=True)
        return queryset.filter(
            Q(cadpro_origem_id__in=visible) | Q(cadpro_destino_id__in=visible)
        ).distinct()

    def perform_create(self, serializer):
        origin = serializer.validated_data["cadpro_origem"]
        destination = serializer.validated_data["cadpro_destino"]
        exigir_acesso_cadpro(self.request.user, origin, papeis=PAPEIS_OPERACAO)
        exigir_acesso_cadpro(self.request.user, destination, papeis=PAPEIS_OPERACAO)
        serializer.save()

    def update(self, request, *args, **kwargs):
        if self.get_object().status != TransferenciaGraos.Status.RASCUNHO:
            return Response(
                {"detail": "Somente transferências em rascunho podem ser editadas."},
                status=status.HTTP_409_CONFLICT,
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        transfer = self.get_object()
        if transfer.status != TransferenciaGraos.Status.RASCUNHO:
            return Response(
                {"detail": "Somente transferências em rascunho podem ser excluídas."},
                status=status.HTTP_409_CONFLICT,
            )
        exigir_acesso_cadpro(request.user, transfer.cadpro_origem, papeis=PAPEIS_GESTAO)
        exigir_acesso_cadpro(request.user, transfer.cadpro_destino, papeis=PAPEIS_GESTAO)
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=("post",))
    def confirmar(self, request, pk=None):
        try:
            transfer = confirmar_transferencia(self.get_object(), usuario=request.user)
        except (ProducaoError, serializers.ValidationError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(self.get_serializer(transfer).data)

    @action(detail=True, methods=("post",))
    def estornar(self, request, pk=None):
        reason = str(request.data.get("motivo", "")).strip()
        if not reason:
            return Response({"motivo": ["Informe o motivo do estorno."]}, status=status.HTTP_400_BAD_REQUEST)
        try:
            transfer = estornar_transferencia(
                self.get_object(),
                usuario=request.user,
                motivo=reason,
            )
        except ProducaoError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(self.get_serializer(transfer).data)


class NotaFiscalProducaoViewSet(viewsets.ModelViewSet):
    serializer_class = NotaFiscalProducaoSerializer
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    search_fields = ("numero", "serie", "chave_acesso", "cadpro__codigo")
    ordering_fields = ("data_emissao", "numero", "valor")

    def get_queryset(self):
        queryset = NotaFiscalProducao.objects.select_related(
            "propriedade",
            "cadpro",
            "recebimento",
            "embarque",
            "criado_por",
        )
        return filtrar_queryset_por_cadpro(queryset, self.request.user)

    def perform_create(self, serializer):
        cadpro = serializer.validated_data["cadpro"]
        exigir_acesso_cadpro(self.request.user, cadpro, papeis=PAPEIS_GESTAO)
        nota = serializer.save()
        registrar_auditoria_enterprise(
            usuario=self.request.user,
            acao="nota_fiscal_criada",
            objeto=nota,
            cadpro=cadpro,
        )

    def perform_update(self, serializer):
        cadpro = serializer.validated_data.get("cadpro", serializer.instance.cadpro)
        exigir_acesso_cadpro(self.request.user, cadpro, papeis=PAPEIS_GESTAO)
        serializer.save()


class ConfiguracaoCulturaViewSet(EscopoGlobalViewSetMixin, viewsets.ModelViewSet):
    queryset = ConfiguracaoCultura.objects.select_related("cultura")
    serializer_class = ConfiguracaoCulturaSerializer
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    search_fields = ("cultura__nome",)
    ordering_fields = ("cultura__nome", "umidade_alerta_percentual", "estoque_minimo_kg")


class DetalheLocalArmazenagemViewSet(EscopoPropriedadeViewSetMixin, viewsets.ModelViewSet):
    queryset = DetalheLocalArmazenagem.objects.select_related("local__propriedade")
    serializer_class = DetalheLocalArmazenagemSerializer
    property_filter = "local__propriedade_id"
    property_path = "local.propriedade"
    property_input_path = "local.propriedade"
    write_roles = PAPEIS_GESTAO
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    search_fields = ("local__nome", "tipo")
    ordering_fields = ("local__nome", "tipo", "capacidade_kg")

    def get_queryset(self):
        queryset = self.queryset
        if self.request.user.is_superuser:
            return queryset
        properties = propriedades_visiveis(self.request.user)
        return queryset.filter(
            Q(local__propriedade__in=properties) | Q(local__propriedade__isnull=True)
        )


class OrigemTerceiroRecebimentoViewSet(viewsets.ModelViewSet):
    serializer_class = OrigemTerceiroRecebimentoSerializer

    def get_queryset(self):
        queryset = OrigemTerceiroRecebimento.objects.select_related(
            "recebimento__propriedade",
            "recebimento__cadpro",
            "terceiro",
        )
        return filtrar_queryset_por_cadpro(
            queryset,
            self.request.user,
            "recebimento__cadpro",
        )

    def perform_create(self, serializer):
        receipt = serializer.validated_data["recebimento"]
        exigir_acesso_cadpro(self.request.user, receipt.cadpro, papeis=PAPEIS_GESTAO)
        serializer.save()


class AuditoriaProducaoEnterpriseViewSet(AuditoriaProducaoViewSet):
    def get_queryset(self):
        queryset = AuditoriaProducao.objects.select_related(
            "propriedade",
            "usuario",
            "escopo_cadpro__cadpro",
        )
        if self.request.user.is_superuser:
            return queryset
        visible_cadpros = cadpros_visiveis(self.request.user).values_list("id", flat=True)
        return queryset.filter(
            Q(escopo_cadpro__cadpro_id__in=visible_cadpros)
            | Q(escopo_cadpro__isnull=True, usuario=self.request.user)
        ).distinct()


class ImportacaoPlanilhaEnterpriseViewSet(ImportacaoPlanilhaViewSet):
    def get_queryset(self):
        queryset = ImportacaoPlanilha.objects.select_related(
            "propriedade",
            "cadpro",
            "criado_por",
        )
        if self.request.user.is_superuser:
            return queryset
        return queryset.filter(
            criado_por=self.request.user,
            propriedade__in=propriedades_visiveis(self.request.user),
        )

    def create(self, request, *args, **kwargs):
        uploaded = request.FILES.get("arquivo")
        if not uploaded:
            return Response({"arquivo": ["Envie uma planilha."]}, status=status.HTTP_400_BAD_REQUEST)
        try:
            validate_upload(uploaded)
            property_id = int(request.data.get("propriedade"))
            property_obj = propriedades_visiveis(request.user).filter(pk=property_id).first()
            if not property_obj:
                return Response(
                    {"propriedade": ["Propriedade não encontrada."]},
                    status=status.HTTP_404_NOT_FOUND,
                )
            exigir_acesso_propriedade(request.user, property_obj, papeis=PAPEIS_GESTAO)
            cadpro_id = request.data.get("cadpro") or None
            cadpro = (
                cadpros_visiveis(request.user, property_id).filter(pk=cadpro_id).first()
                if cadpro_id
                else None
            )
            if cadpro_id and not cadpro:
                return Response(
                    {"cadpro": ["CAD/PRO não autorizado."]},
                    status=status.HTTP_404_NOT_FOUND,
                )
            import_type = request.data.get("tipo")
            if import_type not in ImportacaoPlanilha.Tipo.values:
                return Response(
                    {"tipo": ["Tipo de importação inválido."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
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
                status=(
                    ImportacaoPlanilha.Status.VALIDADA
                    if not preview["errors"]
                    else ImportacaoPlanilha.Status.ENVIADA
                ),
                criado_por=request.user,
            )
            registrar_auditoria_enterprise(
                usuario=request.user,
                acao="planilha_enviada",
                objeto=record,
                propriedade=property_obj,
                cadpro=cadpro,
                metadados={"total_linhas": record.total_linhas},
            )
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except IntegrityError:
            return Response(
                {"detail": "Esta planilha já foi enviada por este usuário para o mesmo tipo."},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(self.get_serializer(record).data, status=status.HTTP_201_CREATED)

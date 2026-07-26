import json

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.access import PAPEIS_GESTAO, exigir_acesso_propriedade, propriedades_visiveis

from .grain_access import cadpros_visiveis
from .grain_imports import file_hash, preview_import, validate_upload
from .grain_models import ImportacaoPlanilha
from .grain_services import ProducaoError, confirmar_embarque, confirmar_recebimento
from .grain_views import (
    EmbarqueProducaoViewSet,
    ImportacaoPlanilhaViewSet,
    RecebimentoProducaoViewSet,
)


class RecebimentoProducaoSeguroViewSet(RecebimentoProducaoViewSet):
    @action(detail=True, methods=("post",))
    def confirmar(self, request, pk=None):
        try:
            receipt = confirmar_recebimento(self.get_object(), usuario=request.user)
        except (ProducaoError, DjangoValidationError) as exc:
            detail = getattr(exc, "message_dict", None) or str(exc)
            return Response(
                detail if isinstance(detail, dict) else {"detail": detail},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(self.get_serializer(receipt).data)


class EmbarqueProducaoSeguroViewSet(EmbarqueProducaoViewSet):
    @action(detail=True, methods=("post",))
    def confirmar(self, request, pk=None):
        try:
            shipment = confirmar_embarque(self.get_object(), usuario=request.user)
        except (ProducaoError, DjangoValidationError) as exc:
            detail = getattr(exc, "message_dict", None) or str(exc)
            return Response(
                detail if isinstance(detail, dict) else {"detail": detail},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(self.get_serializer(shipment).data)


class ImportacaoPlanilhaSeguraViewSet(ImportacaoPlanilhaViewSet):
    def create(self, request, *args, **kwargs):
        uploaded = request.FILES.get("arquivo")
        if not uploaded:
            return Response(
                {"arquivo": ["Envie uma planilha."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            validate_upload(uploaded)
            property_id = int(request.data.get("propriedade"))
            property_obj = propriedades_visiveis(request.user).filter(pk=property_id).first()
            if not property_obj:
                return Response(
                    {"propriedade": ["Propriedade não encontrada."]},
                    status=status.HTTP_404_NOT_FOUND,
                )
            exigir_acesso_propriedade(
                request.user,
                property_obj,
                papeis=PAPEIS_GESTAO,
            )
            cadpro_id = request.data.get("cadpro")
            if not cadpro_id:
                return Response(
                    {"cadpro": ["Informe o CAD/PRO da importação."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            cadpro = cadpros_visiveis(request.user, property_id).filter(pk=cadpro_id).first()
            if not cadpro:
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
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except IntegrityError:
            return Response(
                {"detail": "Esta planilha já foi enviada por este usuário para o mesmo tipo."},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(
            self.get_serializer(record).data,
            status=status.HTTP_201_CREATED,
        )

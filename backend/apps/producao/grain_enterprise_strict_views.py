from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.access import PAPEIS_GESTAO, PAPEIS_OPERACAO

from .grain_access import cadpros_visiveis, exigir_acesso_cadpro
from .grain_enterprise_models import TransferenciaGraos
from .grain_enterprise_services import registrar_auditoria_enterprise
from .grain_enterprise_views import (
    NotaFiscalProducaoViewSet,
    OrigemTerceiroRecebimentoViewSet,
    TransferenciaGraosViewSet,
)
from .grain_models import RecebimentoProducao


def _papeis_transferencia(origin, destination):
    if (
        origin.propriedade_id != destination.propriedade_id
        or origin.id != destination.id
    ):
        return PAPEIS_GESTAO
    return PAPEIS_OPERACAO


class TransferenciaGraosStrictViewSet(TransferenciaGraosViewSet):
    permission_classes = (IsAuthenticated,)

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
            cadpro_origem_id__in=visible,
            cadpro_destino_id__in=visible,
        )

    def perform_create(self, serializer):
        origin = serializer.validated_data["cadpro_origem"]
        destination = serializer.validated_data["cadpro_destino"]
        roles = _papeis_transferencia(origin, destination)
        exigir_acesso_cadpro(self.request.user, origin, papeis=roles)
        exigir_acesso_cadpro(self.request.user, destination, papeis=roles)
        transfer = serializer.save()
        registrar_auditoria_enterprise(
            usuario=self.request.user,
            acao="transferencia_criada",
            objeto=transfer,
            propriedade=transfer.propriedade_origem,
            cadpro=origin,
            metadados={"cadpro_destino": destination.id},
        )

    def perform_update(self, serializer):
        current = serializer.instance
        origin = serializer.validated_data.get("cadpro_origem", current.cadpro_origem)
        destination = serializer.validated_data.get("cadpro_destino", current.cadpro_destino)
        roles = _papeis_transferencia(origin, destination)
        exigir_acesso_cadpro(self.request.user, current.cadpro_origem, papeis=roles)
        exigir_acesso_cadpro(self.request.user, current.cadpro_destino, papeis=roles)
        exigir_acesso_cadpro(self.request.user, origin, papeis=roles)
        exigir_acesso_cadpro(self.request.user, destination, papeis=roles)
        serializer.save()


class NotaFiscalProducaoStrictViewSet(NotaFiscalProducaoViewSet):
    permission_classes = (IsAuthenticated,)

    def perform_update(self, serializer):
        current = serializer.instance
        cadpro = serializer.validated_data.get("cadpro", current.cadpro)
        exigir_acesso_cadpro(self.request.user, current.cadpro, papeis=PAPEIS_GESTAO)
        exigir_acesso_cadpro(self.request.user, cadpro, papeis=PAPEIS_GESTAO)
        anteriores = {
            "numero": current.numero,
            "serie": current.serie,
            "chave_acesso": current.chave_acesso,
            "valor": str(current.valor) if current.valor is not None else None,
        }
        note = serializer.save()
        registrar_auditoria_enterprise(
            usuario=self.request.user,
            acao="nota_fiscal_atualizada",
            objeto=note,
            cadpro=cadpro,
            anteriores=anteriores,
        )

    def destroy(self, request, *args, **kwargs):
        note = self.get_object()
        exigir_acesso_cadpro(request.user, note.cadpro, papeis=PAPEIS_GESTAO)
        return Response(
            {
                "detail": (
                    "Notas fiscais de produção não podem ser excluídas. "
                    "Corrija o documento ou registre o estorno do fluxo vinculado."
                )
            },
            status=status.HTTP_409_CONFLICT,
        )


class OrigemTerceiroRecebimentoStrictViewSet(OrigemTerceiroRecebimentoViewSet):
    permission_classes = (IsAuthenticated,)

    def perform_update(self, serializer):
        current = serializer.instance
        receipt = serializer.validated_data.get("recebimento", current.recebimento)
        exigir_acesso_cadpro(self.request.user, current.recebimento.cadpro, papeis=PAPEIS_GESTAO)
        exigir_acesso_cadpro(self.request.user, receipt.cadpro, papeis=PAPEIS_GESTAO)
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        origin = self.get_object()
        exigir_acesso_cadpro(request.user, origin.recebimento.cadpro, papeis=PAPEIS_GESTAO)
        if origin.recebimento.status != RecebimentoProducao.Status.RASCUNHO:
            return Response(
                {
                    "detail": (
                        "A origem de terceiro não pode ser removida após a confirmação "
                        "do recebimento."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )
        return super().destroy(request, *args, **kwargs)

from django.db import transaction
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from .grain_services import ProducaoError, registrar_auditoria
from .joint_models import LoteConjuntoProducao
from .joint_services import confirmar_lote
from .joint_views import LoteConjuntoProducaoViewSet


class LoteConjuntoProducaoSeguroViewSet(LoteConjuntoProducaoViewSet):
    """Compatibiliza a confirmação com rateio manual posterior.

    A escolha do modo manual identifica a intenção do usuário, mas nenhuma quantidade
    individual é inventada. A confirmação cria primeiro o saldo conjunto; a
    distribuição ocorre somente na action `ratear-manual`, após valores e
    justificativa explícitos.
    """

    @action(detail=True, methods=("post",))
    @transaction.atomic
    def confirmar(self, request, pk=None):
        lote = self.get_object()
        modo_original = lote.modo_rateio
        if modo_original == LoteConjuntoProducao.ModoRateio.MANUAL:
            lote.modo_rateio = LoteConjuntoProducao.ModoRateio.SEM_RATEIO
            lote.save(update_fields=("modo_rateio", "atualizado_em"))
        try:
            confirmado = confirmar_lote(lote, usuario=request.user)
            if modo_original == LoteConjuntoProducao.ModoRateio.MANUAL:
                confirmado.modo_rateio = LoteConjuntoProducao.ModoRateio.MANUAL
                confirmado.save(update_fields=("modo_rateio", "atualizado_em"))
                registrar_auditoria(
                    usuario=request.user,
                    acao="lote_conjunto_rateio_manual_pendente",
                    objeto=confirmado,
                    metadados={
                        "modo_rateio": "manual",
                        "saldo_permanece_conjunto": True,
                        "motivo": "Aguardando quantidades e justificativa explícitas.",
                    },
                )
            return Response(self.get_serializer(confirmado).data)
        except ProducaoError as exc:
            transaction.set_rollback(True)
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

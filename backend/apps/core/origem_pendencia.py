from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.accounts.access import pode
from apps.accounts.views import NoStoreResponseMixin
from apps.graos.models import PendenciaConferencia, CargaColhida, EntradaProducaoTerceiro, ConferenciaEstoque, FechamentoPeriodo


class OrigemPendenciaView(NoStoreResponseMixin, APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, pk):
        if not any(pode(request.user, m, "consultar") for m in ("cargas", "producao-saldos")):
            raise PermissionDenied()
        p = get_object_or_404(PendenciaConferencia, pk=pk)
        d = p.detalhes
        if d.get("origem") in ("propria", "terceiro"):
            if not pode(request.user, "cargas", "consultar"):
                raise PermissionDenied()
            modelo = CargaColhida if d["origem"] == "propria" else EntradaProducaoTerceiro
            numero = d.get("registro")
            campos = ("cultura", "safra", "placa", "motorista", "peso_bruto_kg", "tara_kg", "peso_liquido_kg", "observacoes")
            tipo = "Carga própria" if d["origem"] == "propria" else "Entrada de terceiro"
        elif d.get("contagem"):
            if not pode(request.user, "producao-saldos", "consultar"):
                raise PermissionDenied()
            modelo, numero, tipo = ConferenciaEstoque, d["contagem"], "Contagem física"
            campos = ("cultura", "safra", "data_contagem", "contado_kg", "saldo_proprio_kg", "saldo_terceiros_kg", "justificativa")
        elif d.get("fechamento"):
            modelo, numero, tipo = FechamentoPeriodo, d["fechamento"], "Fechamento de período"
            campos = ("cultura", "safra", "inicio", "fim", "saldo_proprio_kg", "saldo_terceiros_kg", "justificativa")
        else:
            raise ValidationError("Esta pendência não possui registro de origem identificado.")
        obj = get_object_or_404(modelo, pk=numero)
        dados = {c: str(getattr(obj, c)) if getattr(obj, c, None) is not None else None for c in campos}
        dados["armazem"] = obj.armazem.nome
        if isinstance(obj, ConferenciaEstoque):
            dados["diferenca_kg"] = str(obj.contado_kg - obj.saldo_proprio_kg - obj.saldo_terceiros_kg)
        if isinstance(obj, CargaColhida):
            dados.update(propriedade=obj.propriedade.nome, cad_pro=obj.cad_pro.codigo, situacao=obj.status)
        if isinstance(obj, EntradaProducaoTerceiro):
            dados.update(depositante=obj.depositante, saldo_kg=str(obj.saldo_kg), situacao="Cancelado" if obj.movimentos.filter(tipo="entrada", estorno__isnull=False).exists() else "Ativo")
        return Response({"tipo": tipo, "numero": obj.pk, "campos": dados})

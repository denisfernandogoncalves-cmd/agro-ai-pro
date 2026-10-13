import hashlib
import json
from uuid import UUID

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.access import pode
from apps.accounts.views import NoStoreResponseMixin
from apps.graos.models import CargaColhida
from apps.graos.serializers import CargaColhidaSerializer
from apps.graos.views import CargaColhidaViewSet
from .models import ReciboSincronizacao


class ConflitoSincronizacao(APIException):
    status_code = 409
    default_detail = "Registro alterado no servidor. Confira as duas versões antes de sincronizar."


def hash_dados(dados):
    return hashlib.sha256(json.dumps(dados, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


def servidor_id():
    return hashlib.sha256(("agro-offline-v1:" + settings.SECRET_KEY).encode()).hexdigest()


class ContextoOfflineView(NoStoreResponseMixin, APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        if not pode(request.user, "cargas", "consultar"):
            raise PermissionDenied()
        return Response({"servidor": servidor_id(), "usuario": request.user.pk,
                         "modulos": ["cargas"], "versao": 1})


class SincronizarCargaView(NoStoreResponseMixin, APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        dados = request.data
        if not isinstance(dados, dict) or dados.get("servidor") != servidor_id():
            raise ValidationError("A operação pertence a outro servidor ou está incompleta.")
        if type(dados.get("usuario")) is not int or dados["usuario"] != request.user.pk:
            raise PermissionDenied("A operação pertence a outra conta.")
        if not isinstance(dados.get("dados"), dict):
            raise ValidationError("Informe os dados da carga.")
        try:
            operacao = UUID(str(dados["operacao"]))
            dispositivo = UUID(str(dados["dispositivo"]))
        except (ValueError, KeyError, TypeError) as exc:
            raise ValidationError("Identificadores de sincronização inválidos.") from exc
        alvo = dados.get("registro")
        if alvo is not None and (isinstance(alvo, bool) or not isinstance(alvo, int) or alvo < 1):
            raise ValidationError("Registro inválido.")
        acao = "editar" if alvo is not None else "cadastrar"
        if not pode(request.user, "cargas", "consultar") or not pode(request.user, "cargas", acao):
            raise PermissionDenied()
        # Serializa reenvios do mesmo usuário inclusive quando ainda não há recibo.
        get_user_model().objects.select_for_update().get(pk=request.user.pk)
        assinatura = hash_dados(dados)
        recibo = ReciboSincronizacao.objects.filter(usuario=request.user, operacao=operacao).first()
        if recibo:
            if recibo.hash_payload != assinatura:
                raise ConflitoSincronizacao("Operação já recebida com conteúdo diferente. Preserve o identificador e confira a confirmação.")
            return Response(recibo.resultado)
        carga = None
        if alvo is not None:
            carga = CargaColhida.objects.select_for_update().filter(pk=alvo).first()
            if carga is None:
                raise ConflitoSincronizacao("A carga original não está mais disponível.")
            versao = hash_dados(CargaColhidaSerializer(carga, context={"request": request}).data)
            if dados.get("versao_original") != versao:
                raise ConflitoSincronizacao()
        # Reutiliza a view oficial: regras, permissões, auditoria e pendências.
        requisicao_data = request.data
        request._full_data = dados["dados"]
        try:
            view = CargaColhidaViewSet()
            view.request, view.args, view.kwargs = request, (), {"pk": alvo}
            view.format_kwarg = None
            view.action = "partial_update" if alvo is not None else "create"
            resposta = view.update(request, partial=True) if alvo is not None else view.create(request)
        finally:
            request._full_data = requisicao_data
        if resposta.status_code >= 400:
            transaction.set_rollback(True)
            return resposta
        resultado = {"operacao": str(operacao), "registro": resposta.data,
                     "versao": hash_dados(resposta.data)}
        ReciboSincronizacao.objects.create(usuario=request.user, operacao=operacao,
            dispositivo=dispositivo, hash_payload=assinatura, resultado=resultado)
        return Response(resultado, status=200)


class SnapshotCargaView(NoStoreResponseMixin, APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, pk):
        if not pode(request.user, "cargas", "consultar"):
            raise PermissionDenied()
        from django.shortcuts import get_object_or_404
        carga = get_object_or_404(CargaColhida, pk=pk)
        dados = CargaColhidaSerializer(carga, context={"request": request}).data
        return Response({"registro": dados, "versao": hash_dados(dados)})

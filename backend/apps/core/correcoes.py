"""Correções explícitas, com versão e original preservado na auditoria imutável."""
import hashlib
import json
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models.deletion import ProtectedError
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from .models import RegistroAlteracao
from apps.accounts.access import verificar_acesso


def snapshot(instance):
    return json.loads(json.dumps({f.attname: getattr(instance, f.attname) for f in instance._meta.concrete_fields}, default=str))


def versao_correcao(instance):
    return hashlib.sha256(json.dumps(snapshot(instance), sort_keys=True).encode()).hexdigest()


class VersaoCorrecaoSerializer(serializers.Serializer):
    versao_correcao = serializers.SerializerMethodField()

    def get_versao_correcao(self, obj):
        return versao_correcao(obj)


class EdicaoVersionadaMixin:
    """Protege edições de modelos sem timestamp usando o snapshot existente."""

    def update(self, request, *args, **kwargs):
        with transaction.atomic():
            instancia = self.get_queryset().select_for_update(of=("self",)).get(pk=self.get_object().pk)
            original = request.data.get("versao_correcao_original")
            if not isinstance(original, str) or not original:
                raise ValidationError({"versao_correcao_original": "Reabra o registro para obter a versão original."})
            if original != versao_correcao(instancia):
                return Response({"detail": "Este registro mudou desde a abertura. Recarregue para conferir; suas alterações não foram salvas."}, status=409)
            serializer = self.get_serializer(instancia, data=request.data, partial=kwargs.get("partial", False))
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data)


class CorrecaoHistoricoMixin:
    campos_correcao = ()
    modulo_correcao = ""

    def executar_correcao(self, request, cancelar=False):
        verificar_acesso(request.user, request.path, "DELETE" if cancelar else "PATCH")
        motivo = request.data.get("motivo_correcao")
        if not isinstance(motivo, str) or not motivo.strip() or len(motivo) > 500:
            raise ValidationError({"motivo_correcao": "Informe o motivo (até 500 caracteres)."})
        try:
            with transaction.atomic():
                consulta = self.get_object()
                self.bloquear_dependencias(consulta)
                instancia = self.get_queryset().select_for_update(of=("self",)).get(pk=consulta.pk)
                if request.data.get("versao_correcao_original") != versao_correcao(instancia):
                    return Response({"detail": "Registro alterado. Atualize a consulta antes de corrigir ou cancelar."}, status=409)
                original = snapshot(instancia)
                identidade = instancia.pk
                if cancelar:
                    self.cancelar_historico(instancia, request)
                else:
                    campos = self.get_serializer(instancia).fields
                    dados = {}
                    for nome in self.campos_correcao:
                        if nome in request.data:
                            # Somente a lista explícita de correção libera campos antes calculados/encerrados.
                            campos[nome].read_only = False
                            dados[nome] = campos[nome].run_validation(request.data[nome])
                    if not dados:
                        raise ValidationError("Informe ao menos um campo para corrigir.")
                    self.corrigir_historico(instancia, dados, request)
                if instancia.pk:
                    instancia.refresh_from_db()
                atual = snapshot(instancia) if instancia.pk else {}
                RegistroAlteracao.objects.create(usuario=request.user, usuario_nome=request.user.username,
                    modulo=self.modulo_correcao, entidade=str(instancia._meta.verbose_name), registro_id=str(identidade),
                    acao="cancelar" if cancelar else "corrigir",
                    alteracoes={"registro_original": {"antes": original, "depois": atual}, "motivo": {"antes": None, "depois": motivo.strip()}})
                return Response(self.get_serializer(instancia).data) if instancia.pk else Response(status=204)
        except DjangoValidationError as exc:
            raise ValidationError(getattr(exc, "message_dict", None) or exc.messages) from exc
        except ProtectedError as exc:
            raise ValidationError("Este registro possui vínculos. Corrija ou cancele os registros vinculados antes de cancelá-lo.") from exc

    @action(detail=True, methods=["patch"], url_path="corrigir")
    def corrigir(self, request, pk=None):
        return self.executar_correcao(request)

    @action(detail=True, methods=["delete"], url_path="cancelar-registro")
    def cancelar_registro(self, request, pk=None):
        return self.executar_correcao(request, cancelar=True)

    def corrigir_historico(self, instancia, dados, request):
        serializer = self.get_serializer(instancia, data=dados, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

    def bloquear_dependencias(self, instancia):
        pass

    def cancelar_historico(self, instancia, request):
        instancia.delete()

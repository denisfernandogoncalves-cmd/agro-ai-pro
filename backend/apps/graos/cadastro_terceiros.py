from django.db import transaction, IntegrityError
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.accounts.access import pode
from apps.accounts.views import NoStoreResponseMixin
from apps.core.models import RegistroAlteracao
from .models import TerceiroCadastro


class TerceiroCadastroSerializer(serializers.ModelSerializer):
    codigo = serializers.CharField(max_length=40)
    class Meta:
        model = TerceiroCadastro
        fields = ("id", "codigo", "nome", "ativo")

    def validate_codigo(self, valor):
        codigo = valor.strip().upper()
        existentes = TerceiroCadastro.objects.filter(codigo=codigo)
        if self.instance:
            existentes = existentes.exclude(pk=self.instance.pk)
        if existentes.exists():
            raise serializers.ValidationError("Já existe um terceiro com este código.")
        return codigo

    def create(self,dados):
        try:
            with transaction.atomic():
                return super().create(dados)
        except IntegrityError as exc:
            raise serializers.ValidationError({'codigo':'Código já registrado. Atualize o cadastro.'}) from exc

    def update(self,instance,dados):
        try:
            with transaction.atomic():
                return super().update(instance,dados)
        except IntegrityError as exc:
            raise serializers.ValidationError({'codigo':'Código já registrado. Atualize o cadastro.'}) from exc


class CadastroTerceirosView(NoStoreResponseMixin, APIView):
    permission_classes = (IsAuthenticated,)

    def verificar(self, user, acao):
        if not pode(user, "cargas", acao):
            raise PermissionDenied()

    def get(self, request):
        self.verificar(request.user, "consultar")
        return Response(TerceiroCadastroSerializer(TerceiroCadastro.objects.all(), many=True).data)

    def post(self, request):
        self.verificar(request.user, "cadastrar")
        s = TerceiroCadastroSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        with transaction.atomic():
            c = s.save()
            RegistroAlteracao.objects.create(usuario=request.user, usuario_nome=request.user.username, modulo="cargas", entidade="terceiro_cadastro", registro_id=str(c.pk), acao="criar", alteracoes={"depois":s.data})
        return Response(s.data, status=201)

    def patch(self, request, pk):
        self.verificar(request.user, "editar")
        with transaction.atomic():
            c = get_object_or_404(TerceiroCadastro.objects.select_for_update(), pk=pk)
            antes = TerceiroCadastroSerializer(c).data
            s = TerceiroCadastroSerializer(c, data=request.data, partial=True)
            s.is_valid(raise_exception=True)
            s.save()
            RegistroAlteracao.objects.create(usuario=request.user, usuario_nome=request.user.username, modulo="cargas", entidade="terceiro_cadastro", registro_id=str(c.pk), acao="editar", alteracoes={"antes":antes,"depois":s.data})
        return Response(s.data)

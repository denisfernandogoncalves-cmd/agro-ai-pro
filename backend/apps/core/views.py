from django.db import IntegrityError, transaction
from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from apps.accounts.access import pode
from apps.accounts.views import NoStoreResponseMixin
from .models import FavoritoFiltro, RegistroAlteracao
from .serializers import CONTEXTOS, FavoritoSerializer, HistoricoSerializer
from .painel import construir_painel


class PainelView(NoStoreResponseMixin, APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        propriedade = request.query_params.get("propriedade") or None
        safra = request.query_params.get("safra", "").strip()
        if propriedade and (not propriedade.isdigit() or len(propriedade) > 12):
            raise serializers.ValidationError({"propriedade": "Informe uma propriedade válida."})
        if len(safra) > 20:
            raise serializers.ValidationError({"safra": "Safra inválida."})
        return Response(construir_painel(request.user, propriedade, safra))


class FavoritosView(NoStoreResponseMixin, generics.ListCreateAPIView):
    serializer_class = FavoritoSerializer
    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = None

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return FavoritoFiltro.objects.none()
        contexto = self.request.query_params.get("contexto", "")
        permitidos = [item for item in CONTEXTOS if pode(self.request.user, item)]
        queryset = FavoritoFiltro.objects.filter(usuario=self.request.user, contexto__in=permitidos)
        return queryset.filter(contexto=contexto) if contexto else queryset

    def perform_create(self, serializer):
        try:
            with transaction.atomic():
                get_user_model().objects.select_for_update().get(pk=self.request.user.pk)
                if FavoritoFiltro.objects.filter(usuario=self.request.user).count() >= 100:
                    raise serializers.ValidationError("O limite é 100 filtros favoritos por usuário.")
                serializer.save(usuario=self.request.user)
        except IntegrityError:
            raise serializers.ValidationError({"nome": "Já existe um favorito com este nome nesta consulta."})


class FavoritoDetailView(NoStoreResponseMixin, generics.DestroyAPIView):
    serializer_class = FavoritoSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return FavoritoFiltro.objects.none()
        return FavoritoFiltro.objects.filter(usuario=self.request.user)


class HistoricoPaginacao(PageNumberPagination):
    page_size = 25
    page_size_query_param = "por_pagina"
    max_page_size = 100


class HistoricoView(NoStoreResponseMixin, generics.ListAPIView):
    permission_classes = (permissions.IsAdminUser,)
    serializer_class = HistoricoSerializer
    pagination_class = HistoricoPaginacao

    def get_queryset(self):
        queryset = RegistroAlteracao.objects.all()
        for campo in ("modulo", "registro_id", "acao", "usuario_nome"):
            valor = self.request.query_params.get(campo)
            if valor:
                queryset = queryset.filter(**{campo: valor})
        return queryset

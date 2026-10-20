from collections import Counter
from django.db import transaction
from django.utils import timezone
from django.db.models.deletion import ProtectedError
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from apps.accounts.access import pode
from rest_framework import filters, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.core.pagination import PaginacaoOpcional

from .models import Propriedade
from .serializers import PropriedadeSerializer


class PropriedadeViewSet(viewsets.ModelViewSet):
    queryset = Propriedade.objects.prefetch_related(
        "vinculos_cadpro__cad_pro",
        "linhas_importacao",
    ).order_by("nome", "id")
    serializer_class = PropriedadeSerializer
    pagination_class = PaginacaoOpcional
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["nome", "apelido", "proprietario", "municipio", "uf", "cad_pro_identificacao", "vinculos_cadpro__cad_pro__codigo"]
    ordering_fields = ["nome", "municipio", "area_hectares", "criado_em"]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == 'list' and self.request.query_params.get('incluir_arquivadas') != 'true':
            qs = qs.filter(arquivada_em__isnull=True)
        return qs

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def arquivar(self, request, pk=None):
        return self._alterar_arquivo(request, True)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def restaurar(self, request, pk=None):
        return self._alterar_arquivo(request, False)

    def _alterar_arquivo(self, request, arquivar):
        if not pode(request.user, 'propriedades', 'excluir' if arquivar else 'editar'):
            raise PermissionDenied('Seu usuário não pode ' + ('arquivar' if arquivar else 'restaurar') + ' propriedades.')
        propriedade = self.get_queryset().select_for_update().get(pk=self.get_object().pk)
        if bool(propriedade.arquivada_em) != arquivar:
            propriedade.arquivada_em = timezone.now() if arquivar else None
            propriedade.save(update_fields=('arquivada_em',))
        return Response(self.get_serializer(propriedade).data)

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError as erro:
            nomes = {'talhao':'talhões', 'cadpropropriedade':'vínculos CAD/PRO',
                     'linhaimportacao':'linhas de importação', 'cargacolhida':'cargas colhidas',
                     'rateiocargacolhida':'rateios de cargas', 'lotegraos':'lotes de grãos',
                     'posicaosaldograos':'posições de saldo', 'previsaoclima':'previsões de clima'}
            contagens = Counter(nomes.get(obj._meta.model_name, str(obj._meta.verbose_name_plural)) for obj in erro.protected_objects)
            vinculos = ', '.join(f'{quantidade} {nome}' for nome, quantidade in sorted(contagens.items()))
            return Response(
                {'detail': f'A propriedade possui registros vinculados ({vinculos}) e não pode ser excluída. Use Arquivar para retirá-la da lista sem apagar o histórico.'},
                status=status.HTTP_409_CONFLICT,
            )

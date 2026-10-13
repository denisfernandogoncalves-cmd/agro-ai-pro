from django.db import transaction
from django.utils.dateparse import parse_datetime
from rest_framework.response import Response

class EdicaoConcorrenteMixin:
    def update(self, request, *args, **kwargs):
        with transaction.atomic():
            instancia=self.get_queryset().select_for_update(of=("self",)).get(pk=self.get_object().pk)
            esperado=request.data.get("atualizado_em_original")
            if esperado is None:
                return Response({"atualizado_em_original": "Informe a versão original do registro para editar com segurança."},status=400)
            try:
                versao_original = parse_datetime(str(esperado)) if esperado is not None else None
            except (ValueError, TypeError):
                return Response({"detail":"Data original de edição inválida."},status=400)
            if versao_original is None:
                return Response({"atualizado_em_original": "Informe uma data original de edição válida."},status=400)
            if versao_original != instancia.atualizado_em:
                return Response({"detail":"Este registro mudou desde a abertura. Recarregue para conferir; suas alterações não foram salvas."},status=409)
            serializer=self.get_serializer(instancia,data=request.data,partial=kwargs.get("partial",False))
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data)

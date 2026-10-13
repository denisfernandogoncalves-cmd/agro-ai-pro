"""Filtros e paginação das consultas de romaneios, sem alterar lançamentos."""
import unicodedata
from django.db.models import CharField, Value
from django.db.models.functions import Lower, Replace
from django.utils import timezone
from rest_framework import serializers


class FiltrosRomaneiosSerializer(serializers.Serializer):
    busca = serializers.CharField(max_length=160, required=False, allow_blank=True, default="")
    inicio = serializers.DateField(required=False)
    fim = serializers.DateField(required=False)
    historico = serializers.BooleanField(default=False)
    pagina = serializers.IntegerField(min_value=1, max_value=1000000, default=1)
    por_pagina = serializers.ChoiceField(choices=(5, 10, 20), default=5)
    ordem = serializers.ChoiceField(choices=("recentes", "antigos"), default="recentes")

    def validate(self, dados):
        if dados.get("inicio") and dados.get("fim") and dados["inicio"] > dados["fim"]:
            raise serializers.ValidationError({"fim": "A data final deve ser igual ou posterior à inicial."})
        return dados


def normalizar_busca(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto.strip().lower()) if not unicodedata.combining(c))


def texto_sem_acentos(expressao):
    expressao = Lower(expressao, output_field=CharField())
    for caracteres, substituto in (("áàâãä", "a"), ("éèêë", "e"), ("íìîï", "i"), ("óòôõö", "o"), ("úùûü", "u"), ("ç", "c")):
        for caractere in caracteres:
            expressao = Replace(expressao, Value(caractere), Value(substituto))
    return expressao


def filtrar_periodo(queryset, campo, filtros):
    for parametro, lookup in (("inicio", "gte"), ("fim", "lte")):
        if filtros.get(parametro):
            queryset = queryset.filter(**{f"{campo}__{lookup}": filtros[parametro]})
    return queryset


def pagina_romaneios(total, filtros):
    tamanho = int(filtros["por_pagina"])
    paginas = max(1, (total + tamanho - 1) // tamanho)
    pagina = min(filtros["pagina"], paginas)
    inicio = (pagina - 1) * tamanho
    return {"total": total, "pagina": pagina, "paginas": paginas, "por_pagina": tamanho,
            "inicio": inicio + 1 if total else 0, "fim": min(inicio + tamanho, total),
            "consultado_em": timezone.now().isoformat()}, inicio

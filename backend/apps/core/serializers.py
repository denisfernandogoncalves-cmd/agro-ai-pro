import json
from rest_framework import serializers
from apps.accounts.access import pode
from .models import FavoritoFiltro, RegistroAlteracao

CONTEXTOS = {
    "relatorios": {"cad_pro", "propriedade", "proprietario", "cultura", "safra", "classificacao_codigo", "armazem", "destinado_semente", "motorista", "placa", "numero_contrato", "comprador", "data_inicio", "data_fim", "secao", "pagina", "por_pagina"},
    "financeiro": {"search", "tipo", "status", "parceiro", "recebedor", "dataReferencia", "inicio", "fim"},
    "cargas": {"search", "mostrarHistorico", "cultura", "safra", "propriedade"},
    "transferencias": {"search", "mostrarHistorico", "cultura", "safra", "propriedade"},
    "producao-saldos": {"cad_pro", "propriedade", "cultura", "safra", "classificacao_codigo", "armazem"},
    "vendas": {"mostrar_excluidas", "status", "search", "cad_pro", "propriedade", "cultura", "safra", "classificacao_codigo", "armazem", "data_inicio", "data_fim", "numero_contrato", "comprador", "motorista", "placa"},
}


class FavoritoSerializer(serializers.ModelSerializer):
    class Meta:
        model = FavoritoFiltro
        fields = ("id", "contexto", "nome", "filtros", "configuracao", "criado_em")
        read_only_fields = ("id", "criado_em")

    def validate(self, attrs):
        contexto = attrs.get("contexto", self.instance.contexto if self.instance else None)
        if contexto not in CONTEXTOS or not pode(self.context["request"].user, contexto):
            raise serializers.ValidationError("Você não pode salvar filtros para este módulo.")
        config = attrs.get("configuracao", {})
        colunas = {"propriedade", "proprietario", "cad_pro", "cultura", "area", "kg", "sacas", "outros", "semente", "media", "armazenagens"}
        if not isinstance(config, dict) or set(config) - {"colunas", "orientacao", "densidade"} or (config and contexto != "relatorios"):
            raise serializers.ValidationError({"configuracao": "Configuração inválida para este relatório."})
        if "colunas" in config and (not isinstance(config["colunas"], list) or not config["colunas"] or any(not isinstance(c,str) or c not in colunas for c in config["colunas"]) or len(config["colunas"]) > len(colunas)):
            raise serializers.ValidationError({"configuracao": "Selecione colunas válidas."})
        if config.get("orientacao", "paisagem") not in ("retrato", "paisagem") or config.get("densidade", "normal") not in ("normal", "compacta"):
            raise serializers.ValidationError({"configuracao": "Impressão inválida."})
        filtros = attrs.get("filtros", {})
        if not isinstance(filtros, dict) or set(filtros) - CONTEXTOS[contexto]:
            raise serializers.ValidationError({"filtros": "Há filtros inválidos para este módulo."})
        if any(not isinstance(valor, (str, int, bool, type(None))) or isinstance(valor, str) and len(valor) > 250 for valor in filtros.values()) or len(json.dumps(filtros)) > 5000:
            raise serializers.ValidationError({"filtros": "Filtro muito extenso ou em formato inválido."})
        if FavoritoFiltro.objects.filter(usuario=self.context["request"].user, contexto=contexto, nome=attrs.get("nome")).exists():
            raise serializers.ValidationError({"nome": "Já existe um favorito com este nome nesta consulta."})
        return attrs


class HistoricoSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegistroAlteracao
        fields = ("id", "usuario_nome", "modulo", "entidade", "registro_id", "acao", "alteracoes", "criado_em")

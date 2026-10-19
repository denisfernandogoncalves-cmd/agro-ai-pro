"""Busca de leitura nos dados de negócio, limitada pelas permissões do setor."""
import unicodedata
from django.apps import apps
from django.db import connection, models
from django.db.models import Q, TextField, Func, Value
from django.db.models.functions import Cast, Lower
from rest_framework import permissions, serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.access import permissoes_do_usuario


SETORES = {
    'propriedades': 'propriedades', 'talhoes': 'talhoes', 'cadpro': 'propriedades',
    'financeiro': 'financeiro', 'graos': 'producao-saldos', 'vendas': 'vendas',
    'estoque': 'estoque', 'producao': 'operacoes', 'maquinas': 'maquinas',
    'transportes': 'transportes', 'importacoes': 'importacoes',
}
EXCECOES = {
    'graos.CargaColhida': 'cargas', 'graos.RateioCargaColhida': 'cargas',
    'graos.EntradaProducaoTerceiro': 'cargas', 'graos.TerceiroCadastro': 'cargas',
    'graos.MovimentoProducaoTerceiro': 'cargas', 'graos.ArmazemGraos': 'cadastros-agricolas',
    'graos.GrupoColheita': 'talhoes', 'graos.CorrecaoTransferenciaSaldo': 'transferencias',
    'estoque.ProdutoEstoque': 'cadastros-agricolas', 'estoque.LocalEstoque': 'cadastros-agricolas',
    'estoque.CargaCavaco': 'cavaco', 'estoque.FaturamentoInsumo': 'faturamento-insumos',
    'estoque.BaixaFaturamentoInsumo': 'faturamento-insumos',
}
OCULTOS = {'consulta_adapar', 'chave_idempotencia', 'idempotency_key', 'hash', 'fingerprint'}


def normalizar(texto):
    return ''.join(c for c in unicodedata.normalize('NFD', str(texto).casefold()) if not unicodedata.combining(c))


class BuscaGeralView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        termo = request.query_params.get('q', '').strip()
        if len(termo) > 100:
            raise serializers.ValidationError({'q': 'Use até 100 caracteres.'})
        if not termo:
            return Response({'resultados': [], 'limitado': False})
        permissoes = permissoes_do_usuario(request.user)
        resultados, limitado = [], False
        for app, setor in SETORES.items():
            for model in apps.get_app_config(app).get_models():
                modulo = EXCECOES.get(model._meta.label, setor)
                if model._meta.label == 'estoque.ProdutoEstoque':
                    modulo = next((m for m in ('cadastros-agricolas', 'estoque', 'operacoes', 'faturamento-insumos') if 'consultar' in permissoes.get(m, [])), modulo)
                if 'consultar' not in permissoes.get(modulo, []):
                    continue
                campos = [f for f in model._meta.concrete_fields if not f.is_relation
                          and f.name not in OCULTOS and not isinstance(f, (models.BinaryField, models.FileField))
                          and (f.editable or f.primary_key)
                          and isinstance(f, (models.CharField, models.TextField, models.IntegerField,
                                             models.DecimalField, models.FloatField, models.DateField, models.UUIDField))]
                qs = model.objects.all()
                destino = modulo
                if model._meta.label == 'talhoes.GrupoPropriedadesColheita':
                    destino = 'grupos-colheita'
                    qs = qs.filter(excluido_em__isnull=True)
                consulta = Q()
                for indice, campo in enumerate(campos):
                    alias = f'busca_{indice}'
                    expressao = Cast(campo.name, TextField())
                    busca = termo
                    if connection.vendor == 'postgresql':
                        expressao = Func(Lower(expressao), Value('áàâãäéèêëíìîïóòôõöúùûüçñ'), Value('aaaaaeeeeiiiiooooouuuucn'), function='TRANSLATE', output_field=TextField())
                        busca = normalizar(termo)
                    qs = qs.annotate(**{alias: expressao})
                    consulta |= Q(**{f'{alias}__icontains': busca})
                if not campos:
                    continue
                linhas = list(qs.filter(consulta).order_by('pk').values(*[f.name for f in campos])[:6])
                limitado = limitado or len(linhas) > 5
                for linha in linhas[:5]:
                    correspondencias = [f'{f.verbose_name}: {linha[f.name]}' for f in campos
                                        if linha[f.name] is not None and normalizar(termo) in normalizar(linha[f.name])]
                    titulo = next((str(linha[n]) for n in ('nome', 'descricao', 'codigo', 'placa', 'numero_documento') if linha.get(n)), f'{model._meta.verbose_name} #{linha[model._meta.pk.name]}')
                    resultados.append({'modulo': destino, 'tipo': str(model._meta.verbose_name),
                                       'id': str(linha[model._meta.pk.name]), 'titulo': titulo[:160],
                                       'resumo': ' · '.join(correspondencias)[:240]})
        return Response({'resultados': resultados, 'limitado': limitado})

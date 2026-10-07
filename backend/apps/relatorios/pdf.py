"""PDF de conferência, com filtros, critérios, totais e todos os detalhes limitados."""
from io import BytesIO
from xml.sax.saxutils import escape
from django.http import HttpResponse
from rest_framework import permissions, serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from apps.accounts.access import pode
from apps.accounts.views import NoStoreResponseMixin
from apps.core.excel import consulta_consistente
from .excel import achatar, CRITERIOS
from .serializers import FiltrosRelatorioOperacionalSerializer
from .selectors import selecionar_relatorio_operacional


class RelatorioPdfView(NoStoreResponseMixin, APIView):
    permission_classes=(permissions.IsAuthenticated,)

    def get(self,request):
        if not pode(request.user,'relatorios','consultar') or not pode(request.user,'relatorios','imprimir'):
            raise PermissionDenied()
        serializer=FiltrosRelatorioOperacionalSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        with consulta_consistente():
            dados=selecionar_relatorio_operacional(**{**serializer.validated_data,'pagina':1,'por_pagina':1000})
            if dados['dados']['total']>1000:
                raise serializers.ValidationError('PDF limitado a 1.000 registros. Reduza os filtros ou exporte em Excel; nenhum resultado foi omitido.')
            buffer=BytesIO();styles=getSampleStyleSheet();story=[]
            def texto(rotulo,valor):
                story.append(Paragraph(f'<b>{escape(str(rotulo))}</b>: {escape(str(valor))}',styles['BodyText']))
                story.append(Spacer(1,4))
            texto('AGRO-AI-PRO',f"Relatório {dados['secao']} — {dados['dados']['total']} registros")
            for chave,valor in dados['filtros'].items():texto('Filtro '+chave,valor)
            for chave,valor in CRITERIOS:texto(chave,valor)
            for chave,valor in achatar(dados['totais']).items():texto('Total '+chave,valor)
            if dados['secao']=='producao_propriedade':
                for chave,valor in achatar(dados['totais_producao_propriedade']).items():texto('Total de produção '+chave,valor)
            for n,item in enumerate(dados['dados']['resultados'],1):
                texto('Registro',n)
                for chave,valor in achatar(item).items():texto(chave,valor if valor is not None else '—')
            SimpleDocTemplate(buffer,pagesize=A4,title=f"Relatório {dados['secao']}",leftMargin=36,rightMargin=36).build(story)
        response=HttpResponse(buffer.getvalue(),content_type='application/pdf')
        response['Content-Disposition']=f'attachment; filename="relatorio-{dados["secao"]}.pdf"'
        return response

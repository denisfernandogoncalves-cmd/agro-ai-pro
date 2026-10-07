from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied
from apps.accounts.access import pode
from apps.accounts.views import NoStoreResponseMixin
from apps.vendas.romaneios import _numero
from .models import MovimentoProducaoTerceiro
from .romaneios_terceiros import gerar_pdf, gerar_excel


class RomaneioRetiradaView(NoStoreResponseMixin,APIView):
    permission_classes=(IsAuthenticated,)
    excel=False
    tipo='saida'

    def get(self,request,pk):
        if not pode(request.user,'cargas','imprimir'):
            raise PermissionDenied()
        if self.tipo == 'transferencia' and not pode(request.user,'transferencias','imprimir'):
            raise PermissionDenied()
        m=get_object_or_404(MovimentoProducaoTerceiro.objects.select_related('entrada__armazem','criado_por','estorno','movimentacao_saldo__posicao__propriedade','movimentacao_saldo__posicao__cad_pro'),pk=pk,tipo=self.tipo)
        s=m.snapshot_depois
        campos=[('Retirada',f'#{m.pk}'),('Terceiro',s.get('depositante',m.entrada.depositante)),('Data',m.data_movimento.strftime('%d/%m/%Y')),('Produto / safra',f"{s.get('cultura',m.entrada.cultura)} / {s.get('safra',m.entrada.safra)}"),('Armazém',s.get('armazem_nome',m.entrada.armazem.nome)),('Quantidade retirada',f'{_numero(m.quantidade_kg)} kg'),('Destino',m.destino),('Motorista / placa',f"{m.motorista or '—'} / {m.placa or '—'}"),('Documento',m.documento or '—'),('Saldo anterior',f'{_numero(m.saldo_anterior_kg)} kg'),('Saldo após retirada',f'{_numero(m.saldo_posterior_kg)} kg'),('Responsável',m.criado_por.username),('Situação','Estornada' if hasattr(m,'estorno') else 'Registrada'),('Observações',m.observacoes or '—')]
        nome='retirada'
        if self.tipo == 'transferencia':
            nome='transferencia'
            posicao=m.movimentacao_saldo.posicao
            campos=[('Transferência',f'#{m.pk}'),('Terceiro de origem',s.get('depositante',m.entrada.depositante)),('Recebimento de origem',f'#{m.entrada_id}'),('Data',m.data_movimento.strftime('%d/%m/%Y')),('Produto / safra',f"{s.get('cultura',m.entrada.cultura)} / {s.get('safra',m.entrada.safra)}"),('Armazém',s.get('armazem_nome',m.entrada.armazem.nome)),('Destinatário no registro',m.destino),('Propriedade destinatária (cadastro atual)',posicao.propriedade.nome),('CAD/PRO destinatário (cadastro atual)',posicao.cad_pro.codigo),('Quantidade transferida',f'{_numero(m.quantidade_kg)} kg'),('Saldo anterior do terceiro',f'{_numero(m.saldo_anterior_kg)} kg'),('Saldo após transferência',f'{_numero(m.saldo_posterior_kg)} kg'),('Documento',m.documento or '—'),('Motivo',m.observacoes or '—'),('Responsável',m.criado_por.username),('Situação','Estornada' if hasattr(m,'estorno') else 'Registrada'),('Contabilidade','Somente estoque: não integra produção, área, média ou produtividade.')]
        conteudo=(gerar_excel if self.excel else gerar_pdf)(m,campos=campos,titulo=f'{nome.upper()} DE TERCEIROS #{pk}')
        r=HttpResponse(conteudo,content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' if self.excel else 'application/pdf')
        ext='xlsx' if self.excel else 'pdf'
        r['Content-Disposition']=f'attachment; filename="{nome}-terceiro-{pk}.{ext}"'
        return r

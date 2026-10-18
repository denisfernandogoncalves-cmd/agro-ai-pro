from django.db import transaction
from apps.financeiro.origens import sincronizar_conta_origem
from .models import CompraDiesel


@transaction.atomic
def sincronizar_conta_diesel(compra):
    origem = CompraDiesel.objects.select_for_update().get(pk=compra.pk)
    dados = dict(tipo='pagar', descricao=f'Compra diesel {origem.tipo} #{origem.pk} · {origem.fornecedor} · {origem.produtor}'[:220], valor=origem.valor_total, data_emissao=origem.data, data_vencimento=origem.vencimento, recebedor_nome=origem.fornecedor) if origem.vencimento else None
    sincronizar_conta_origem(origem, dados, f'Origem: compra de diesel #{origem.pk}. Produtor: {origem.produtor}. Pagamento indicado na compra: {origem.get_pagamento_display()}. Baixa somente após confirmação no Financeiro.')
    compra.conta_pagar_id = origem.conta_pagar_id

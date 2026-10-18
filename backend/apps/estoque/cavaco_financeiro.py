from django.db import transaction
from apps.financeiro.origens import sincronizar_conta_origem
from .models import CargaCavaco


@transaction.atomic
def sincronizar_conta_cavaco(carga):
    origem = CargaCavaco.objects.select_for_update().get(pk=carga.pk)
    dados = dict(tipo='pagar', descricao=f'Cavaco — carga #{origem.pk} · {origem.fornecedor}'[:220], valor=origem.total, data_emissao=origem.data, data_vencimento=origem.data_vencimento or origem.data, recebedor_nome=origem.fornecedor)
    sincronizar_conta_origem(origem, dados, f'Origem: carga de cavaco #{origem.pk}. Pagamento indicado na origem: {"pago" if origem.pago else "pendente"}. Conta criada pendente por solicitação do Product Owner; conferir e baixar no Financeiro.')
    carga.conta_pagar_id = origem.conta_pagar_id

"""Executar via manage.py shell; ensaio padrão com rollback. APLICAR=True confirma."""
from django.db import transaction
from apps.estoque.models import CompraEstoque
from apps.estoque.compra_financeiro import sincronizar_compra_financeiro
from apps.core.models import RegistroAlteracao

with transaction.atomic():
    novos = 0
    for compra in CompraEstoque.objects.order_by("pk"):
        anterior = compra.conta_pagar_id
        conta = sincronizar_compra_financeiro(compra)
        if not anterior and conta:
            novos += 1
            RegistroAlteracao.objects.create(usuario=None, usuario_nome="Sistema — integração autorizada pelo Product Owner", modulo="financeiro", entidade="Compra de estoque", registro_id=str(compra.pk), acao="editar", alteracoes={"conta_pagar": {"antes":None, "depois":conta.pk}, "integracao": {"antes":None,"depois":"Compras no Financeiro; execução técnica, sem sessão humana."}})
        print(str(compra.pk), conta.pk if conta else None, str(conta.valor) if conta else "0", conta.status if conta else "sem valor")
    print("Títulos novos:", novos, "Aplicar:", globals().get("APLICAR", False))
    if not globals().get("APLICAR", False):
        transaction.set_rollback(True)

"""Obrigações novas: origem e título são gravados na mesma transação."""
from django.db import models, transaction
from rest_framework.exceptions import ValidationError


class OrigemFinanceira(models.Model):
    integrar_financeiro = models.BooleanField(default=True, editable=False)
    conta_pagar = models.OneToOneField(
        "financeiro.LancamentoFinanceiro", null=True, blank=True, editable=False,
        on_delete=models.PROTECT, related_name="%(app_label)s_%(class)s_origem",
    )

    class Meta:
        abstract = True

    @transaction.atomic
    def save(self, *args, **kwargs):
        if set(kwargs.get("update_fields") or ()) == {"conta_pagar"}:
            return super().save(*args, **kwargs)
        if self._state.adding and (getattr(self, "chave_importacao", None) or getattr(self, "base_por_aba", False)):
            self.integrar_financeiro = False
        if not self._state.adding:
            anterior = type(self).objects.select_for_update().get(pk=self.pk)
            self.conta_pagar_id = anterior.conta_pagar_id
            self.integrar_financeiro = anterior.integrar_financeiro
        resultado = super().save(*args, **kwargs)
        sincronizar(self)
        return resultado

    @transaction.atomic
    def delete(self, *args, **kwargs):
        origem = type(self).objects.select_for_update().get(pk=self.pk)
        cancelar_conta(origem)
        return super().delete(*args, **kwargs)


def cancelar_conta(origem):
    from .models import LancamentoFinanceiro
    from .services import cancelar_lancamento
    if origem.conta_pagar_id:
        conta = LancamentoFinanceiro.objects.select_for_update().get(pk=origem.conta_pagar_id)
        if conta.status == "liquidado":
            raise ValidationError("A origem possui conta liquidada. Confira a baixa no Financeiro antes de cancelar.")
        if conta.status == "pendente":
            cancelar_lancamento(conta)


@transaction.atomic
def sincronizar(origem):
    from .origens import sincronizar_conta_origem
    if not origem.integrar_financeiro:
        return
    # Releitura bloqueada evita criar dois títulos para a mesma origem.
    atual = type(origem).objects.select_for_update().get(pk=origem.pk)
    dados = atual.dados_conta_pagar()
    if dados is None or dados["valor"] <= 0:
        cancelar_conta(atual)
    else:
        if atual.conta_pagar_id:
            dados["data_vencimento"] = atual.conta_pagar.data_vencimento
        atual.excluido_em = None
        sincronizar_conta_origem(atual, dados,
            "Integração automática de lançamento novo. Sem vencimento específico, "
            "usa a data da origem; conferir vencimento e liquidar no Financeiro.")
    origem.conta_pagar_id = atual.conta_pagar_id


def dados_conta(descricao, valor, data, **campos):
    return dict(tipo="pagar", descricao=descricao[:220], valor=valor,
                data_emissao=data, data_vencimento=data, **campos)

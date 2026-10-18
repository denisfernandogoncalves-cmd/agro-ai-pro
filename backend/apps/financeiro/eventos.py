"""Comissões acompanham as fontes usadas pelo holerite existente."""
from django.db import transaction
from django.db.models.signals import post_save, post_delete, pre_delete
from django.dispatch import receiver
from apps.transportes.models import LancamentoTransporte, RemuneracaoMotorista, FreteConferido
from apps.maquinas.models import ManutencaoMaquina
from apps.graos.models import CargaColhida
from apps.vendas.models import EntregaVendaGraos
from .integracao import sincronizar, cancelar_conta


@receiver(post_save, sender=LancamentoTransporte)
@receiver(post_delete, sender=LancamentoTransporte)
@receiver(post_save, sender=FreteConferido)
@receiver(post_delete, sender=FreteConferido)
@receiver(post_save, sender=CargaColhida)
@receiver(post_save, sender=EntregaVendaGraos)
def atualizar_comissoes(sender, instance, **kwargs):
    if kwargs.get("raw"):
        return
    # Somente remunerações novas; históricos sem conferência permanecem intactos.
    with transaction.atomic():
        remuneracoes = RemuneracaoMotorista.objects.filter(integrar_financeiro=True).order_by("pk")
        for remuneracao in remuneracoes.select_for_update():
            sincronizar(remuneracao)


@receiver(pre_delete, sender=LancamentoTransporte)
@receiver(pre_delete, sender=RemuneracaoMotorista)
@receiver(pre_delete, sender=ManutencaoMaquina)
def cancelar_titulo_exclusao(sender, instance, **kwargs):
    cancelar_conta(instance)

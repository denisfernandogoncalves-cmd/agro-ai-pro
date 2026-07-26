from django.apps import apps
from django.db.models.signals import post_save
from django.dispatch import receiver

from .grain_enterprise_models import AuditoriaCadPro
from .grain_models import AuditoriaProducao, CadPro


@receiver(post_save, sender=AuditoriaProducao)
def vincular_auditoria_ao_cadpro(sender, instance, created, **kwargs):
    if not created or hasattr(instance, "escopo_cadpro"):
        return
    cadpro = None
    try:
        if instance.entidade == CadPro._meta.label:
            cadpro = CadPro.objects.filter(pk=instance.entidade_id).first()
        elif instance.entidade_id:
            model = apps.get_model(instance.entidade)
            objeto = model._default_manager.filter(pk=instance.entidade_id).first()
            cadpro = (
                getattr(objeto, "cadpro", None)
                or getattr(objeto, "cadpro_origem", None)
                or getattr(objeto, "cadpro_destino", None)
            )
    except (LookupError, ValueError, TypeError):
        return
    if cadpro:
        AuditoriaCadPro.objects.get_or_create(
            auditoria=instance,
            defaults={"cadpro": cadpro},
        )

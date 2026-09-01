from django.db import migrations


def cadastrar_contratos(apps, schema_editor):
    Venda = apps.get_model("vendas", "VendaGraos")
    Contrato = apps.get_model("vendas", "ContratoComercial")
    alias = schema_editor.connection.alias
    for venda in Venda.objects.using(alias).filter(contrato__isnull=True).iterator():
        contrato, _ = Contrato.objects.using(alias).get_or_create(
            numero=venda.numero_contrato, empresa=venda.cliente_nome,
        )
        Venda.objects.using(alias).filter(pk=venda.pk).update(contrato=contrato)


class Migration(migrations.Migration):
    dependencies = [("vendas", "0003_devolucaovendagraos_cancelado_em_and_more")]
    operations = [migrations.RunPython(cadastrar_contratos, migrations.RunPython.noop)]

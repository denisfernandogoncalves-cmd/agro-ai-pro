from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("vendas", "0006_entregavendagraos_motorista")]

    operations = [
        migrations.AlterField(
            model_name="vendagraos",
            name="numero_contrato",
            field=models.CharField(blank=True, max_length=80),
        ),
    ]

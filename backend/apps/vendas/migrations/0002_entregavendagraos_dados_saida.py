from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("vendas", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="entregavendagraos",
            name="destino",
            field=models.CharField(blank=True, max_length=160),
        ),
        migrations.AddField(
            model_name="entregavendagraos",
            name="placa",
            field=models.CharField(blank=True, max_length=12),
        ),
        migrations.AddField(
            model_name="entregavendagraos",
            name="nota_produtor",
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name="entregavendagraos",
            name="nota_empresa",
            field=models.CharField(blank=True, max_length=80),
        ),
    ]

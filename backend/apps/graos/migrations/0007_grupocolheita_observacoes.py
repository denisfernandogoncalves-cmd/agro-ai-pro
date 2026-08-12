from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("graos", "0006_grupocolheita_armazem_padrao"),
    ]

    operations = [
        migrations.AddField(
            model_name="grupocolheita",
            name="observacoes",
            field=models.TextField(blank=True),
        ),
    ]

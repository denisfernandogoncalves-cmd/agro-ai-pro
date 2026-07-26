from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("clima", "0003_clima_automatico"),
    ]

    operations = [
        migrations.AddField(
            model_name="configuracaoclima",
            name="latitude_usada",
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name="configuracaoclima",
            name="longitude_usada",
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name="configuracaoclima",
            name="altitude_usada",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True),
        ),
        migrations.AddField(
            model_name="configuracaoclima",
            name="dados_atuais",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]

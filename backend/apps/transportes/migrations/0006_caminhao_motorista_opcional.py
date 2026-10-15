from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("transportes", "0005_freteconferido")]
    operations = [
        migrations.AlterField(
            model_name="caminhao", name="motorista",
            field=models.CharField(blank=True, max_length=120),
        ),
    ]

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("talhoes", "0003_talhao_geometria_geojson_and_validators"),
    ]
    operations = [
        migrations.AlterField(
            model_name="talhao",
            name="propriedade",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="talhoes",
                to="propriedades.propriedade",
            ),
        ),
    ]

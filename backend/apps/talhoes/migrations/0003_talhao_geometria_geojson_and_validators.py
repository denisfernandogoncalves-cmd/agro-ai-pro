from decimal import Decimal

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("talhoes", "0002_talhao_altitude_media_talhao_arquivo_kml_and_more")]
    operations = [
        migrations.AddConstraint(
            model_name="talhao",
            constraint=models.CheckConstraint(check=models.Q(("area_hectares__gt", 0)), name="talhao_area_positiva"),
        ),
        migrations.AddField(
            model_name="talhao",
            name="geometria_geojson",
            field=models.JSONField(blank=True, editable=False, null=True),
        ),
        migrations.AlterField(
            model_name="talhao",
            name="area_hectares",
            field=models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal("0.01"))]),
        ),
        migrations.AlterField(
            model_name="talhao",
            name="latitude_centro",
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=10, null=True, validators=[django.core.validators.MinValueValidator(Decimal("-90")), django.core.validators.MaxValueValidator(Decimal("90"))]),
        ),
        migrations.AlterField(
            model_name="talhao",
            name="longitude_centro",
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=10, null=True, validators=[django.core.validators.MinValueValidator(Decimal("-180")), django.core.validators.MaxValueValidator(Decimal("180"))]),
        ),
    ]

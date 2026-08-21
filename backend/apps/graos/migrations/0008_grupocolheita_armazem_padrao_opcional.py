from decimal import Decimal

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("graos", "0007_grupocolheita_observacoes"),
    ]

    operations = [
        migrations.AddField(
            model_name="grupocolheita",
            name="desconto_ph_por_ponto",
            field=models.DecimalField(
                decimal_places=3,
                default=Decimal("0.000"),
                max_digits=6,
                validators=[
                    django.core.validators.MinValueValidator(Decimal("0")),
                    django.core.validators.MaxValueValidator(Decimal("100")),
                ],
            ),
        ),
        migrations.AddField(
            model_name="grupocolheita",
            name="ph_minimo",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.00"),
                max_digits=5,
                validators=[
                    django.core.validators.MinValueValidator(Decimal("0")),
                    django.core.validators.MaxValueValidator(Decimal("100")),
                ],
            ),
        ),
        migrations.AddField(
            model_name="cargacolhida",
            name="motorista",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AlterField(
            model_name="cargacolhida",
            name="placa",
            field=models.CharField(blank=True, default="", max_length=7),
        ),
        migrations.AddField(
            model_name="cargacolhida",
            name="contexto_colheita",
            field=models.JSONField(default=dict),
        ),
        migrations.AlterField(
            model_name="grupocolheita",
            name="armazem_padrao",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="grupos_colheita_padrao",
                to="graos.armazemgraos",
            ),
        ),
    ]

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("vendas", "0009_entregavendagraos_avariados_percentual_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="contratocomercial",
            name="preco_venda",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=16,
                null=True,
                validators=[MinValueValidator(Decimal("0.01"))],
            ),
        ),
        migrations.AddField(
            model_name="contratocomercial",
            name="unidade_preco",
            field=models.CharField(
                choices=[("kg", "kg"), ("sc", "saca")],
                default="kg",
                max_length=2,
            ),
        ),
    ]

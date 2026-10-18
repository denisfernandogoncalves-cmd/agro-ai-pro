from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("estoque", "0012_compra_financeiro")]
    operations = [
        migrations.AddField(model_name="compraestoque", name="integrar_financeiro",
                            field=models.BooleanField(default=False, editable=False)),
        migrations.AlterField(model_name="compraestoque", name="integrar_financeiro",
                              field=models.BooleanField(default=True, editable=False)),
    ]

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [migrations.CreateModel(
        name="ReciboSincronizacao",
        fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("operacao", models.UUIDField()),
            ("dispositivo", models.UUIDField()),
            ("hash_payload", models.CharField(max_length=64)),
            ("resultado", models.JSONField()),
            ("criado_em", models.DateTimeField(auto_now_add=True)),
            ("usuario", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
        ],
        options={"constraints": [models.UniqueConstraint(fields=("usuario", "operacao"), name="offline_usuario_operacao_unica")]},
    )]

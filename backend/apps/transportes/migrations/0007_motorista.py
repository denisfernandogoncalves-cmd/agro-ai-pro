from django.db import migrations, models


def copiar_motoristas(apps, schema_editor):
    Motorista = apps.get_model("transportes", "Motorista")
    nomes = set()
    for entidade in ("Caminhao", "LancamentoTransporte", "RemuneracaoMotorista"):
        nomes.update(apps.get_model("transportes", entidade).objects.using(schema_editor.connection.alias).values_list("motorista", flat=True))
    for nome in sorted({nome.strip() for nome in nomes if nome and nome.strip()}):
        Motorista.objects.using(schema_editor.connection.alias).get_or_create(nome=nome)


class Migration(migrations.Migration):
    dependencies = [("transportes", "0006_caminhao_motorista_opcional")]
    operations = [
        migrations.CreateModel(name="Motorista", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("nome", models.CharField(max_length=120, unique=True)),
            ("apelido", models.CharField(blank=True, max_length=80)),
            ("ativo", models.BooleanField(default=True)),
        ], options={"ordering": ("nome", "id")}),
        migrations.RunPython(copiar_motoristas, migrations.RunPython.noop),
    ]

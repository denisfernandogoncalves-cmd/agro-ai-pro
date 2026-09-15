from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("talhoes", "0007_talhao_area_calculada_hectares"),
        ("cadpro", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="GrupoPropriedadesColheita",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=100, unique=True)),
                ("ativo", models.BooleanField(default=True)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("vinculos", models.ManyToManyField(to="cadpro.cadpropropriedade")),
            ],
            options={"ordering": ("nome", "id")},
        ),
    ]

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def vincular_superusuarios(apps, schema_editor):
    AcessoPropriedade = apps.get_model("propriedades", "AcessoPropriedade")
    Propriedade = apps.get_model("propriedades", "Propriedade")
    app_label, model_name = settings.AUTH_USER_MODEL.split(".")
    Usuario = apps.get_model(app_label, model_name)

    propriedades = list(Propriedade.objects.all())
    for usuario in Usuario.objects.filter(is_superuser=True):
        AcessoPropriedade.objects.bulk_create(
            [
                AcessoPropriedade(
                    propriedade=propriedade,
                    usuario=usuario,
                    papel="administrador",
                    ativo=True,
                )
                for propriedade in propriedades
            ],
            ignore_conflicts=True,
        )


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("propriedades", "0003_propriedade_area_calculada_hectares_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="AcessoPropriedade",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "papel",
                    models.CharField(
                        choices=[
                            ("administrador", "Administrador"),
                            ("gestor", "Gestor"),
                            ("operador", "Operador"),
                            ("leitura", "Somente leitura"),
                        ],
                        default="leitura",
                        max_length=16,
                    ),
                ),
                ("ativo", models.BooleanField(default=True)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                (
                    "propriedade",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="acessos",
                        to="propriedades.propriedade",
                    ),
                ),
                (
                    "usuario",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="acessos_propriedades",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("propriedade__nome", "usuario__username"),
                "indexes": [
                    models.Index(
                        fields=["usuario", "ativo"],
                        name="prop_acesso_usuario_idx",
                    ),
                    models.Index(
                        fields=["propriedade", "papel"],
                        name="prop_acesso_papel_idx",
                    ),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("propriedade", "usuario"),
                        name="propriedade_usuario_acesso_unico",
                    )
                ],
            },
        ),
        migrations.RunPython(
            vincular_superusuarios,
            migrations.RunPython.noop,
        ),
    ]

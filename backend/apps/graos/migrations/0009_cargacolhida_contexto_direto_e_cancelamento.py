import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def preencher_contexto_direto(apps, schema_editor):
    CargaColhida = apps.get_model("graos", "CargaColhida")
    MovimentacaoGraos = apps.get_model("graos", "MovimentacaoGraos")

    for carga in CargaColhida.objects.select_related(
        "grupo_colheita", "armazem", "lote"
    ).iterator():
        grupo = carga.grupo_colheita
        divergencias = []
        if carga.armazem.propriedade_id != grupo.propriedade_id:
            divergencias.append("propriedade/armazém")
        if carga.lote.cad_pro_id != grupo.cad_pro_id:
            divergencias.append("CAD/PRO/lote")
        if carga.lote.cultura.casefold() != grupo.cultura.casefold():
            divergencias.append("cultura/lote")
        if carga.lote.safra != grupo.safra:
            divergencias.append("safra/lote")
        contexto_colheita = carga.contexto_colheita
        if not isinstance(contexto_colheita, dict):
            contexto_colheita = {}
        if divergencias:
            contexto_colheita = {
                **contexto_colheita,
                "migracao_contexto_direto": {
                    "versao": "graos.0009",
                    "origem": "armazem_e_lote",
                    "divergencias_grupo_legado": divergencias,
                },
            }
        atualizacao = {
            # O armazém e o lote são as dimensões do saldo físico realmente
            # contabilizado. Em históricos divergentes, eles prevalecem sem
            # apagar o grupo legado e a divergência fica registrada no snapshot.
            "propriedade_id": carga.armazem.propriedade_id,
            "cad_pro_id": carga.lote.cad_pro_id,
            "cultura": carga.lote.cultura,
            "safra": carga.lote.safra,
            "contexto_colheita": contexto_colheita,
        }
        if carga.movimentacao_id:
            estorno = (
                MovimentacaoGraos.objects.filter(estorno_de_id=carga.movimentacao_id)
                .order_by("criado_em", "id")
                .first()
            )
            if estorno:
                atualizacao.update(
                    status="cancelada",
                    cancelada_em=estorno.criado_em,
                    cancelada_por_id=estorno.criado_por_id,
                    motivo_cancelamento=(
                        "Carga marcada como cancelada porque sua movimentação de "
                        "produção já possuía estorno antes desta migração."
                    ),
                )
        CargaColhida.objects.filter(pk=carga.pk).update(**atualizacao)


def validar_reversao_contexto_direto(apps, schema_editor):
    CargaColhida = apps.get_model("graos", "CargaColhida")
    if CargaColhida.objects.filter(grupo_colheita__isnull=True).exists():
        raise RuntimeError(
            "Não é seguro reverter graos.0009: existem cargas diretas sem Grupo de "
            "Colheita legado. Preserve a migration e restaure um backup compatível."
        )


class Migration(migrations.Migration):
    dependencies = [
        ("graos", "0008_grupocolheita_armazem_padrao_opcional"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="cargacolhida",
            name="propriedade",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="cargas_colhidas",
                to="propriedades.propriedade",
            ),
        ),
        migrations.AddField(
            model_name="cargacolhida",
            name="cad_pro",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="cargas_colhidas",
                to="cadpro.cadpro",
            ),
        ),
        migrations.AddField(
            model_name="cargacolhida",
            name="cultura",
            field=models.CharField(blank=True, default="", max_length=50),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="cargacolhida",
            name="safra",
            field=models.CharField(blank=True, default="", max_length=20),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="cargacolhida",
            name="status",
            field=models.CharField(
                choices=[
                    ("ativa", "Ativa"),
                    ("cancelada", "Cancelada"),
                    ("substituida", "Substituída por correção"),
                ],
                default="ativa",
                max_length=12,
            ),
        ),
        migrations.AddField(
            model_name="cargacolhida",
            name="cancelada_em",
            field=models.DateTimeField(blank=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name="cargacolhida",
            name="cancelada_por",
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="cargas_colhidas_canceladas",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="cargacolhida",
            name="motivo_cancelamento",
            field=models.TextField(blank=True, editable=False),
        ),
        migrations.AddField(
            model_name="cargacolhida",
            name="substituida_por",
            field=models.OneToOneField(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="carga_anterior",
                to="graos.cargacolhida",
            ),
        ),
        migrations.RunPython(preencher_contexto_direto, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="cargacolhida",
            name="propriedade",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="cargas_colhidas",
                to="propriedades.propriedade",
            ),
        ),
        migrations.AlterField(
            model_name="cargacolhida",
            name="cad_pro",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="cargas_colhidas",
                to="cadpro.cadpro",
            ),
        ),
        migrations.AlterField(
            model_name="cargacolhida",
            name="cultura",
            field=models.CharField(max_length=50),
        ),
        migrations.AlterField(
            model_name="cargacolhida",
            name="safra",
            field=models.CharField(max_length=20),
        ),
        migrations.AlterField(
            model_name="cargacolhida",
            name="grupo_colheita",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="cargas",
                to="graos.grupocolheita",
            ),
        ),
        migrations.RunPython(
            migrations.RunPython.noop,
            validar_reversao_contexto_direto,
        ),
        migrations.AddIndex(
            model_name="cargacolhida",
            index=models.Index(
                fields=["propriedade", "data_colheita"],
                name="graos_carga_prop_data_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="cargacolhida",
            index=models.Index(
                fields=["cad_pro", "cultura", "safra"],
                name="graos_carga_cad_cult_saf_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="cargacolhida",
            index=models.Index(
                fields=["status", "data_colheita"],
                name="graos_carga_status_data_idx",
            ),
        ),
    ]

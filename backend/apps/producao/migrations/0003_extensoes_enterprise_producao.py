# Generated for the enterprise production extensions.

from decimal import Decimal

import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("estoque", "0001_initial"),
        ("financeiro", "0001_initial"),
        ("producao", "0002_gestao_integrada_producao"),
        ("propriedades", "0004_acessopropriedade"),
        ("talhoes", "0007_talhao_area_calculada_hectares"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ConfiguracaoCultura",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("umidade_alerta_percentual", models.DecimalField(decimal_places=2, default=Decimal("14"), max_digits=5, validators=[django.core.validators.MinValueValidator(Decimal("0")), django.core.validators.MaxValueValidator(Decimal("100"))])),
                ("estoque_minimo_kg", models.DecimalField(decimal_places=3, default=Decimal("0"), max_digits=18, validators=[django.core.validators.MinValueValidator(Decimal("0"))])),
                ("observacoes", models.TextField(blank=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("cultura", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="configuracao_producao", to="producao.cultura")),
            ],
            options={"ordering": ("cultura__nome",)},
        ),
        migrations.CreateModel(
            name="DetalheLocalArmazenagem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tipo", models.CharField(choices=[("silo", "Silo"), ("armazem", "Armazém"), ("cooperativa", "Cooperativa"), ("terceiro", "Armazém de terceiro"), ("outro", "Outro")], default="silo", max_length=12)),
                ("capacidade_kg", models.DecimalField(blank=True, decimal_places=3, max_digits=18, null=True, validators=[django.core.validators.MinValueValidator(Decimal("0.001"))])),
                ("latitude", models.DecimalField(blank=True, decimal_places=6, max_digits=10, null=True)),
                ("longitude", models.DecimalField(blank=True, decimal_places=6, max_digits=10, null=True)),
                ("ativo", models.BooleanField(default=True)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("local", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="detalhe_producao", to="estoque.localestoque")),
            ],
            options={"ordering": ("local__nome",)},
        ),
        migrations.CreateModel(
            name="OrigemTerceiroRecebimento",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("documento_origem", models.CharField(blank=True, max_length=80)),
                ("observacoes", models.TextField(blank=True)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("recebimento", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="origem_terceiro", to="producao.recebimentoproducao")),
                ("terceiro", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="recebimentos_producao_terceiros", to="financeiro.parceirofinanceiro")),
            ],
        ),
        migrations.CreateModel(
            name="TransferenciaGraos",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("data", models.DateTimeField(default=django.utils.timezone.now)),
                ("quantidade_kg", models.DecimalField(decimal_places=3, max_digits=18, validators=[django.core.validators.MinValueValidator(Decimal("0.001"))])),
                ("status", models.CharField(choices=[("rascunho", "Rascunho"), ("confirmada", "Confirmada"), ("estornada", "Estornada")], default="rascunho", max_length=12)),
                ("motivo", models.CharField(blank=True, max_length=240)),
                ("confirmado_em", models.DateTimeField(blank=True, null=True)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("cadpro_destino", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="transferencias_recebidas", to="producao.cadpro")),
                ("cadpro_origem", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="transferencias_enviadas", to="producao.cadpro")),
                ("confirmado_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="transferencias_graos_confirmadas", to=settings.AUTH_USER_MODEL)),
                ("criado_por", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="transferencias_graos_criadas", to=settings.AUTH_USER_MODEL)),
                ("cultura", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="transferencias", to="producao.cultura")),
                ("local_destino", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="transferencias_graos_recebidas", to="estoque.localestoque")),
                ("local_origem", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="transferencias_graos_enviadas", to="estoque.localestoque")),
                ("movimento_entrada", models.OneToOneField(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="transferencia_entrada", to="producao.movimentacaograos")),
                ("movimento_saida", models.OneToOneField(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="transferencia_saida", to="producao.movimentacaograos")),
                ("propriedade_destino", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="transferencias_graos_recebidas", to="propriedades.propriedade")),
                ("propriedade_origem", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="transferencias_graos_enviadas", to="propriedades.propriedade")),
                ("safra", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="transferencias", to="producao.safra")),
                ("talhao_destino", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="transferencias_graos_recebidas", to="talhoes.talhao")),
                ("talhao_origem", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="transferencias_graos_enviadas", to="talhoes.talhao")),
            ],
            options={"ordering": ("-data", "-id")},
        ),
        migrations.AddIndex(
            model_name="transferenciagraos",
            index=models.Index(fields=["propriedade_origem", "cadpro_origem", "data"], name="prod_transf_origem_idx"),
        ),
        migrations.AddIndex(
            model_name="transferenciagraos",
            index=models.Index(fields=["propriedade_destino", "cadpro_destino", "data"], name="prod_transf_destino_idx"),
        ),
        migrations.CreateModel(
            name="NotaFiscalProducao",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tipo", models.CharField(choices=[("produtor", "Nota do produtor"), ("empresa", "Nota da empresa"), ("terceiro", "Nota de terceiro")], max_length=12)),
                ("numero", models.CharField(max_length=80)),
                ("serie", models.CharField(blank=True, max_length=20)),
                ("chave_acesso", models.CharField(blank=True, max_length=44, null=True, unique=True)),
                ("data_emissao", models.DateField(default=django.utils.timezone.localdate)),
                ("valor", models.DecimalField(blank=True, decimal_places=2, max_digits=16, null=True, validators=[django.core.validators.MinValueValidator(Decimal("0.01"))])),
                ("arquivo", models.FileField(blank=True, null=True, upload_to="notas/producao/%Y/%m/")),
                ("observacoes", models.TextField(blank=True)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("cadpro", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="notas_fiscais", to="producao.cadpro")),
                ("criado_por", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="notas_fiscais_producao", to=settings.AUTH_USER_MODEL)),
                ("embarque", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="notas_fiscais", to="producao.embarqueproducao")),
                ("propriedade", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="notas_fiscais_producao", to="propriedades.propriedade")),
                ("recebimento", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="notas_fiscais", to="producao.recebimentoproducao")),
            ],
            options={"ordering": ("-data_emissao", "-id")},
        ),
        migrations.AddConstraint(
            model_name="notafiscalproducao",
            constraint=models.UniqueConstraint(fields=("propriedade", "tipo", "numero", "serie"), name="prod_nf_contexto_numero_unico"),
        ),
        migrations.CreateModel(
            name="AuditoriaCadPro",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("auditoria", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="escopo_cadpro", to="producao.auditoriaproducao")),
                ("cadpro", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="auditorias", to="producao.cadpro")),
            ],
            options={"ordering": ("-auditoria__criado_em",)},
        ),
    ]

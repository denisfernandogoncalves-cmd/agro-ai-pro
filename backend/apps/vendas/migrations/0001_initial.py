import django.db.models.deletion
import django.utils.timezone
import django.core.validators
from decimal import Decimal

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("graos", "0007_grupocolheita_observacoes"),
    ]

    operations = [
        migrations.CreateModel(
            name="VendaGraos",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("numero_contrato", models.CharField(max_length=80, unique=True)),
                ("cliente_nome", models.CharField(max_length=160)),
                ("quantidade_kg", models.DecimalField(decimal_places=3, max_digits=16, validators=[django.core.validators.MinValueValidator(Decimal("0.001"))])),
                ("quantidade_entregue_kg", models.DecimalField(decimal_places=3, default=Decimal("0.000"), max_digits=16)),
                ("quantidade_devolvida_kg", models.DecimalField(decimal_places=3, default=Decimal("0.000"), max_digits=16)),
                ("quantidade_cancelada_kg", models.DecimalField(decimal_places=3, default=Decimal("0.000"), max_digits=16)),
                ("data_contrato", models.DateField(default=django.utils.timezone.localdate)),
                ("data_limite_entrega", models.DateField(blank=True, null=True)),
                ("status", models.CharField(choices=[("rascunho", "Rascunho"), ("confirmada", "Confirmada"), ("parcial", "Parcialmente entregue"), ("entregue", "Entregue"), ("cancelada", "Cancelada")], default="rascunho", max_length=12)),
                ("observacoes", models.TextField(blank=True)),
                ("chave_criacao", models.CharField(max_length=120, unique=True)),
                ("hash_criacao", models.CharField(max_length=64)),
                ("chave_confirmacao", models.CharField(blank=True, max_length=120, null=True, unique=True)),
                ("hash_confirmacao", models.CharField(blank=True, max_length=64)),
                ("chave_cancelamento", models.CharField(blank=True, max_length=120, null=True, unique=True)),
                ("hash_cancelamento", models.CharField(blank=True, max_length=64)),
                ("confirmado_em", models.DateTimeField(blank=True, null=True)),
                ("cancelado_em", models.DateTimeField(blank=True, null=True)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("criado_por", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="vendas_graos_criadas", to=settings.AUTH_USER_MODEL)),
                ("lote", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="vendas", to="graos.lotegraos")),
                ("posicao", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="vendas", to="graos.posicaosaldograos")),
                ("reserva", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="venda", to="graos.reservasaldograos")),
            ],
            options={"ordering": ("-data_contrato", "-id")},
        ),
        migrations.CreateModel(
            name="EntregaVendaGraos",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantidade_kg", models.DecimalField(decimal_places=3, max_digits=16)),
                ("data_entrega", models.DateField(default=django.utils.timezone.localdate)),
                ("referencia_externa", models.CharField(blank=True, max_length=120)),
                ("observacoes", models.TextField(blank=True)),
                ("chave_idempotencia", models.CharField(max_length=120, unique=True)),
                ("hash_requisicao", models.CharField(max_length=64)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("criado_por", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="entregas_vendas_graos", to=settings.AUTH_USER_MODEL)),
                ("movimentacao", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="entrega_venda", to="graos.movimentacaograos")),
                ("origem", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="entrega_venda", to="graos.origemsaldograos")),
                ("venda", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="entregas", to="vendas.vendagraos")),
            ],
            options={"ordering": ("-data_entrega", "-id")},
        ),
        migrations.CreateModel(
            name="DevolucaoVendaGraos",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantidade_kg", models.DecimalField(decimal_places=3, max_digits=16)),
                ("data_devolucao", models.DateField(default=django.utils.timezone.localdate)),
                ("referencia_externa", models.CharField(blank=True, max_length=120)),
                ("observacoes", models.TextField(blank=True)),
                ("chave_idempotencia", models.CharField(max_length=120, unique=True)),
                ("hash_requisicao", models.CharField(max_length=64)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("criado_por", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="devolucoes_vendas_graos", to=settings.AUTH_USER_MODEL)),
                ("movimentacao", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="devolucao_venda", to="graos.movimentacaograos")),
                ("origem", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="devolucao_venda", to="graos.origemsaldograos")),
                ("venda", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="devolucoes", to="vendas.vendagraos")),
            ],
            options={"ordering": ("-data_devolucao", "-id")},
        ),
        migrations.AddIndex(model_name="vendagraos", index=models.Index(fields=["status", "data_contrato"], name="vendas_status_data_idx")),
        migrations.AddIndex(model_name="vendagraos", index=models.Index(fields=["posicao", "status"], name="vendas_posicao_status_idx")),
        migrations.AddIndex(model_name="vendagraos", index=models.Index(fields=["cliente_nome"], name="vendas_cliente_idx")),
        migrations.AddConstraint(model_name="vendagraos", constraint=models.CheckConstraint(condition=models.Q(("quantidade_kg__gt", 0)), name="vendas_quantidade_positiva")),
        migrations.AddConstraint(model_name="vendagraos", constraint=models.CheckConstraint(condition=models.Q(("quantidade_entregue_kg__gte", 0)), name="vendas_entregue_nao_negativa")),
        migrations.AddConstraint(model_name="vendagraos", constraint=models.CheckConstraint(condition=models.Q(("quantidade_devolvida_kg__gte", 0)), name="vendas_devolvida_nao_negativa")),
        migrations.AddConstraint(model_name="vendagraos", constraint=models.CheckConstraint(condition=models.Q(("quantidade_cancelada_kg__gte", 0)), name="vendas_cancelada_nao_negativa")),
        migrations.AddConstraint(model_name="vendagraos", constraint=models.CheckConstraint(condition=models.Q(("quantidade_entregue_kg__lte", models.F("quantidade_kg"))), name="vendas_entregue_ate_contratada")),
        migrations.AddConstraint(model_name="vendagraos", constraint=models.CheckConstraint(condition=models.Q(("quantidade_devolvida_kg__lte", models.F("quantidade_entregue_kg"))), name="vendas_devolvida_ate_entregue")),
        migrations.AddConstraint(model_name="vendagraos", constraint=models.CheckConstraint(condition=models.Q(("quantidade_cancelada_kg__lte", models.F("quantidade_kg"))), name="vendas_cancelada_ate_contratada")),
        migrations.AddConstraint(model_name="entregavendagraos", constraint=models.CheckConstraint(condition=models.Q(("quantidade_kg__gt", 0)), name="vendas_entrega_quantidade_positiva")),
        migrations.AddConstraint(model_name="devolucaovendagraos", constraint=models.CheckConstraint(condition=models.Q(("quantidade_kg__gt", 0)), name="vendas_devolucao_quantidade_positiva")),
    ]

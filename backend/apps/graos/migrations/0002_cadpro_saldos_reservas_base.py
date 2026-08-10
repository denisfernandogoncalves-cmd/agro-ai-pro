# Generated manually for the frozen grain-balance contract.

import django.db.models.deletion
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cadpro", "0001_initial"),
        ("graos", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="lotegraos",
            name="cad_pro",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="lotes_graos",
                to="cadpro.cadpro",
            ),
        ),
        migrations.AddField(
            model_name="lotegraos",
            name="classificacao_codigo",
            field=models.CharField(default="PADRAO", max_length=50),
        ),
        migrations.CreateModel(
            name="OrigemSaldoGraos",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tipo", models.CharField(choices=[("producao", "Produção"), ("reserva", "Reserva"), ("liberacao", "Liberação de reserva"), ("entrega", "Entrega"), ("devolucao", "Devolução"), ("ajuste", "Ajuste"), ("estorno", "Estorno"), ("transferencia", "Transferência"), ("reconciliacao", "Reconciliação"), ("legado", "Legado")], max_length=20)),
                ("chave_idempotencia", models.CharField(max_length=160, unique=True)),
                ("referencia_externa", models.CharField(blank=True, max_length=160)),
                ("hash_requisicao", models.CharField(max_length=64)),
                ("metadados", models.JSONField(blank=True, default=dict)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("criado_por", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="origens_saldo_graos", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "origem de saldo de grãos",
                "verbose_name_plural": "origens de saldo de grãos",
                "ordering": ("-criado_em", "-id"),
            },
        ),
        migrations.CreateModel(
            name="PosicaoSaldoGraos",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("cultura", models.CharField(max_length=50)),
                ("safra", models.CharField(max_length=20)),
                ("classificacao_codigo", models.CharField(default="PADRAO", max_length=50)),
                ("saldo_fisico_kg", models.DecimalField(decimal_places=3, default=Decimal("0.000"), max_digits=16)),
                ("saldo_comprometido_kg", models.DecimalField(decimal_places=3, default=Decimal("0.000"), max_digits=16)),
                ("versao", models.PositiveBigIntegerField(default=0)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("armazem", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="posicoes_saldo", to="graos.armazemgraos")),
                ("cad_pro", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="posicoes_saldo_graos", to="cadpro.cadpro")),
            ],
            options={
                "verbose_name": "posição de saldo de grãos",
                "verbose_name_plural": "posições de saldo de grãos",
                "ordering": ("safra", "cultura", "classificacao_codigo", "armazem_id"),
            },
        ),
        migrations.CreateModel(
            name="ReservaSaldoGraos",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantidade_kg", models.DecimalField(decimal_places=3, max_digits=16)),
                ("saldo_reservado_kg", models.DecimalField(decimal_places=3, max_digits=16)),
                ("referencia_externa", models.CharField(blank=True, max_length=160)),
                ("status", models.CharField(choices=[("ativa", "Ativa"), ("parcial", "Parcialmente atendida"), ("concluida", "Concluída"), ("liberada", "Liberada")], default="ativa", max_length=12)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("criado_por", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="reservas_saldo_graos", to=settings.AUTH_USER_MODEL)),
                ("origem", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="reserva_criada", to="graos.origemsaldograos")),
                ("posicao", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="reservas", to="graos.posicaosaldograos")),
            ],
            options={
                "verbose_name": "reserva de saldo de grãos",
                "verbose_name_plural": "reservas de saldo de grãos",
                "ordering": ("-criado_em", "-id"),
            },
        ),
        migrations.AddField(
            model_name="movimentacaograos",
            name="delta_comprometido_kg",
            field=models.DecimalField(decimal_places=3, default=Decimal("0.000"), max_digits=16),
        ),
        migrations.AddField(
            model_name="movimentacaograos",
            name="delta_fisico_kg",
            field=models.DecimalField(decimal_places=3, default=Decimal("0.000"), max_digits=16),
        ),
        migrations.AddField(
            model_name="movimentacaograos",
            name="estorno_de",
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="movimento_estorno", to="graos.movimentacaograos"),
        ),
        migrations.AddField(
            model_name="movimentacaograos",
            name="operacao",
            field=models.CharField(blank=True, choices=[("credito_producao", "Crédito de produção"), ("reserva", "Reserva"), ("liberacao", "Liberação"), ("entrega", "Entrega"), ("devolucao", "Devolução"), ("ajuste", "Ajuste"), ("estorno", "Estorno"), ("transferencia_saida", "Transferência - saída"), ("transferencia_entrada", "Transferência - entrada"), ("legado", "Legado")], max_length=24, null=True),
        ),
        migrations.AddField(
            model_name="movimentacaograos",
            name="origem",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="movimentacoes", to="graos.origemsaldograos"),
        ),
        migrations.AddField(
            model_name="movimentacaograos",
            name="posicao",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="movimentacoes", to="graos.posicaosaldograos"),
        ),
        migrations.AddField(
            model_name="movimentacaograos",
            name="reserva",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="movimentacoes", to="graos.reservasaldograos"),
        ),
        migrations.AddField(
            model_name="movimentacaograos",
            name="snapshot_anterior",
            field=models.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="movimentacaograos",
            name="snapshot_posterior",
            field=models.JSONField(default=dict),
        ),
    ]

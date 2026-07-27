from decimal import Decimal

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("mercado", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ConfiguracaoAtivoMercado",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("ativo", models.CharField(choices=[("soja_cbot", "Soja CBOT"), ("milho_cbot", "Milho CBOT"), ("trigo_cbot", "Trigo CBOT"), ("farelo_soja", "Farelo de soja"), ("oleo_soja", "Óleo de soja"), ("brent", "Petróleo Brent"), ("dolar", "Dólar PTAX")], max_length=24, unique=True)),
                ("habilitado", models.BooleanField(default=True)),
                ("provedor", models.CharField(default="stooq", max_length=40)),
                ("simbolo", models.CharField(max_length=40)),
                ("frequencia_minutos", models.PositiveIntegerField(default=15)),
                ("ultima_tentativa", models.DateTimeField(blank=True, null=True)),
                ("ultima_atualizacao", models.DateTimeField(blank=True, null=True)),
                ("proxima_atualizacao", models.DateTimeField(blank=True, null=True)),
                ("status", models.CharField(choices=[("pendente", "Pendente"), ("atualizado", "Atualizado"), ("erro", "Erro"), ("desatualizado", "Desatualizado"), ("desativado", "Desativado")], default="pendente", max_length=16)),
                ("mensagem_erro", models.CharField(blank=True, max_length=240)),
                ("falhas_consecutivas", models.PositiveIntegerField(default=0)),
                ("total_chamadas", models.PositiveBigIntegerField(default=0)),
                ("total_atualizacoes", models.PositiveBigIntegerField(default=0)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ("ativo",)},
        ),
        migrations.CreateModel(
            name="CotacaoAtivoMercado",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("ativo", models.CharField(choices=[("soja_cbot", "Soja CBOT"), ("milho_cbot", "Milho CBOT"), ("trigo_cbot", "Trigo CBOT"), ("farelo_soja", "Farelo de soja"), ("oleo_soja", "Óleo de soja"), ("brent", "Petróleo Brent"), ("dolar", "Dólar PTAX")], max_length=24)),
                ("intervalo", models.CharField(choices=[("snapshot", "Snapshot"), ("diario", "Diário")], max_length=12)),
                ("data_hora", models.DateTimeField()),
                ("abertura", models.DecimalField(blank=True, decimal_places=6, max_digits=18, null=True)),
                ("maxima", models.DecimalField(blank=True, decimal_places=6, max_digits=18, null=True)),
                ("minima", models.DecimalField(blank=True, decimal_places=6, max_digits=18, null=True)),
                ("fechamento", models.DecimalField(decimal_places=6, max_digits=18, validators=[django.core.validators.MinValueValidator(Decimal("0"))])),
                ("volume", models.DecimalField(blank=True, decimal_places=3, max_digits=22, null=True)),
                ("unidade", models.CharField(max_length=60)),
                ("moeda", models.CharField(default="USD", max_length=12)),
                ("fonte", models.CharField(max_length=80)),
                ("simbolo_origem", models.CharField(blank=True, max_length=40)),
                ("recebido_em", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ("ativo", "data_hora"),
                "indexes": [models.Index(fields=["ativo", "intervalo", "-data_hora"], name="merc_ent_ativo_int_data_idx")],
                "constraints": [
                    models.UniqueConstraint(fields=("ativo", "intervalo", "data_hora"), name="mercado_enterprise_ativo_intervalo_data_unico"),
                    models.CheckConstraint(condition=models.Q(("fechamento__gte", 0)), name="mercado_enterprise_fechamento_nao_negativo"),
                ],
            },
        ),
        migrations.CreateModel(
            name="AtualizacaoMercado",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("ativo", models.CharField(choices=[("soja_cbot", "Soja CBOT"), ("milho_cbot", "Milho CBOT"), ("trigo_cbot", "Trigo CBOT"), ("farelo_soja", "Farelo de soja"), ("oleo_soja", "Óleo de soja"), ("brent", "Petróleo Brent"), ("dolar", "Dólar PTAX")], max_length=24)),
                ("status", models.CharField(choices=[("sucesso", "Sucesso"), ("erro", "Erro"), ("cache", "Cache"), ("ignorada", "Ignorada")], max_length=12)),
                ("iniciada_em", models.DateTimeField()),
                ("finalizada_em", models.DateTimeField()),
                ("provedor", models.CharField(max_length=40)),
                ("chamadas_realizadas", models.PositiveSmallIntegerField(default=0)),
                ("pontos_snapshot", models.PositiveIntegerField(default=0)),
                ("pontos_diarios", models.PositiveIntegerField(default=0)),
                ("utilizou_cache", models.BooleanField(default=False)),
                ("tipo_erro", models.CharField(blank=True, max_length=80)),
                ("mensagem_erro", models.CharField(blank=True, max_length=240)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ("-iniciada_em", "-id"),
                "indexes": [models.Index(fields=["ativo", "-iniciada_em"], name="merc_atual_ativo_data_idx")],
            },
        ),
    ]

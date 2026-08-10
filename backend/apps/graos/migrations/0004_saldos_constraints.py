from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("graos", "0003_normalizar_lotes_existentes")]

    operations = [
        migrations.AlterField(
            model_name="movimentacaograos",
            name="operacao",
            field=models.CharField(choices=[("credito_producao", "Crédito de produção"), ("reserva", "Reserva"), ("liberacao", "Liberação"), ("entrega", "Entrega"), ("devolucao", "Devolução"), ("ajuste", "Ajuste"), ("estorno", "Estorno"), ("transferencia_saida", "Transferência - saída"), ("transferencia_entrada", "Transferência - entrada"), ("legado", "Legado")], max_length=24),
        ),
        migrations.AlterField(
            model_name="movimentacaograos",
            name="origem",
            field=models.ForeignKey(on_delete=models.PROTECT, related_name="movimentacoes", to="graos.origemsaldograos"),
        ),
        migrations.AlterField(
            model_name="movimentacaograos",
            name="posicao",
            field=models.ForeignKey(on_delete=models.PROTECT, related_name="movimentacoes", to="graos.posicaosaldograos"),
        ),
        migrations.AddIndex(
            model_name="lotegraos",
            index=models.Index(fields=["cad_pro", "cultura", "safra", "classificacao_codigo"], name="graos_lote_posicao_idx"),
        ),
        migrations.AddConstraint(
            model_name="lotegraos",
            constraint=models.CheckConstraint(condition=~models.Q(classificacao_codigo=""), name="graos_lote_classificacao_preenchida"),
        ),
        migrations.AddIndex(
            model_name="origemsaldograos",
            index=models.Index(fields=["tipo", "referencia_externa"], name="graos_origem_tipo_ref_idx"),
        ),
        migrations.AddConstraint(
            model_name="posicaosaldograos",
            constraint=models.UniqueConstraint(fields=("cad_pro", "cultura", "safra", "classificacao_codigo", "armazem"), name="graos_posicao_chave_unica"),
        ),
        migrations.AddConstraint(
            model_name="posicaosaldograos",
            constraint=models.CheckConstraint(condition=models.Q(saldo_fisico_kg__gte=0), name="graos_posicao_fisico_nao_negativo"),
        ),
        migrations.AddConstraint(
            model_name="posicaosaldograos",
            constraint=models.CheckConstraint(condition=models.Q(saldo_comprometido_kg__gte=0), name="graos_posicao_comprom_nao_negativo"),
        ),
        migrations.AddConstraint(
            model_name="posicaosaldograos",
            constraint=models.CheckConstraint(condition=models.Q(saldo_comprometido_kg__lte=models.F("saldo_fisico_kg")), name="graos_posicao_comprom_ate_fisico"),
        ),
        migrations.AddIndex(
            model_name="posicaosaldograos",
            index=models.Index(fields=["cad_pro", "cultura", "safra"], name="graos_posicao_cad_cult_idx"),
        ),
        migrations.AddIndex(
            model_name="posicaosaldograos",
            index=models.Index(fields=["armazem", "classificacao_codigo"], name="graos_posicao_arm_class_idx"),
        ),
        migrations.AddConstraint(
            model_name="reservasaldograos",
            constraint=models.CheckConstraint(condition=models.Q(quantidade_kg__gt=0), name="graos_reserva_quantidade_positiva"),
        ),
        migrations.AddConstraint(
            model_name="reservasaldograos",
            constraint=models.CheckConstraint(condition=models.Q(saldo_reservado_kg__gte=0), name="graos_reserva_saldo_nao_negativo"),
        ),
        migrations.AddConstraint(
            model_name="reservasaldograos",
            constraint=models.CheckConstraint(condition=models.Q(saldo_reservado_kg__lte=models.F("quantidade_kg")), name="graos_reserva_saldo_ate_quantidade"),
        ),
        migrations.AddIndex(
            model_name="movimentacaograos",
            index=models.Index(fields=["posicao", "criado_em"], name="graos_mov_posicao_criado_idx"),
        ),
        migrations.AddIndex(
            model_name="movimentacaograos",
            index=models.Index(fields=["origem", "operacao"], name="graos_mov_origem_oper_idx"),
        ),
        migrations.AddConstraint(
            model_name="movimentacaograos",
            constraint=models.CheckConstraint(condition=~models.Q(delta_fisico_kg=0) | ~models.Q(delta_comprometido_kg=0), name="graos_movimento_delta_nao_zero"),
        ),
    ]

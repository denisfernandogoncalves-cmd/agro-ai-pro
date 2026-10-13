from decimal import Decimal, ROUND_HALF_UP



from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator

from django.db import models





class Caminhao(models.Model):

    placa = models.CharField(max_length=7, unique=True, validators=[RegexValidator(r"^[A-Z]{3}[0-9][A-Z0-9][0-9]{2}$", "Informe uma placa brasileira válida.")])

    veiculo = models.CharField(max_length=100)

    motorista = models.CharField(max_length=120)

    ativo = models.BooleanField(default=True)



    class Meta:

        ordering = ("placa",)





class LancamentoTransporte(models.Model):

    caminhao = models.ForeignKey(Caminhao, on_delete=models.PROTECT, related_name="lancamentos")

    motorista = models.CharField(max_length=120)

    data = models.DateField(db_index=True)

    tipo = models.CharField(max_length=7, choices=[("receita", "Receita"), ("despesa", "Despesa")])

    descricao = models.CharField(max_length=200)

    local = models.CharField(max_length=220, blank=True)

    nota = models.CharField(max_length=100, blank=True)

    unidade = models.CharField(max_length=10, blank=True)

    quantidade = models.DecimalField(max_digits=14, decimal_places=4, validators=[MinValueValidator(Decimal("0.0001"))])

    valor_unitario = models.DecimalField(max_digits=14, decimal_places=4, validators=[MinValueValidator(Decimal("0"))])

    origem = models.CharField(max_length=120, blank=True)

    chave_importacao = models.CharField(max_length=64, unique=True, null=True, editable=False)

    criado_em = models.DateTimeField(auto_now_add=True)



    class Meta:

        ordering = ("-data", "-id")

        indexes = [models.Index(fields=["caminhao", "data"])]
        constraints = [
            models.CheckConstraint(condition=models.Q(quantidade__gt=0), name="transporte_quantidade_positiva"),
            models.CheckConstraint(condition=models.Q(valor_unitario__gte=0), name="transporte_valor_nao_negativo"),
        ]



    @property

    def total(self):

        return (self.quantidade * self.valor_unitario).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)





class RemuneracaoMotorista(models.Model):

    caminhao = models.ForeignKey(Caminhao, on_delete=models.PROTECT, related_name="remuneracoes")

    motorista = models.CharField(max_length=120)

    competencia = models.DateField(db_index=True)

    salario = models.DecimalField(max_digits=14, decimal_places=2, default=0, validators=[MinValueValidator(Decimal("0"))])

    comissao = models.DecimalField(max_digits=14, decimal_places=2, default=0, validators=[MinValueValidator(Decimal("0"))])

    base_por_aba = models.BooleanField(default=False, editable=False)
    comissao_percentual = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True, validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))])

    observacoes = models.CharField(max_length=220, blank=True)



    class Meta:

        ordering = ("-competencia", "caminhao__placa", "motorista")

        constraints = [
            models.UniqueConstraint(fields=["caminhao", "motorista", "competencia"], name="transporte_remuneracao_unica"),
            models.CheckConstraint(condition=models.Q(salario__gte=0), name="transporte_salario_nao_negativo"),
            models.CheckConstraint(condition=models.Q(comissao__gte=0), name="transporte_comissao_nao_negativa"),
            models.CheckConstraint(condition=models.Q(comissao_percentual__isnull=True) | models.Q(comissao_percentual__gte=0, comissao_percentual__lte=100), name="transporte_percentual_valido"),
        ]





    @property

    def base_comissao(self):

        from django.db.models import Q

        from .importacao import MESES

        periodo = Q(data__year=self.competencia.year, data__month=self.competencia.month)

        if self.base_por_aba:

            # A competência da aba preserva inclusive datas fora do mês na fonte.

            periodo = (Q(chave_importacao__isnull=False, origem__startswith=MESES[self.competencia.month - 1] + "!", data__year=self.competencia.year) | (Q(chave_importacao__isnull=True) & periodo))

        base = Decimal(0)

        for item in LancamentoTransporte.objects.filter(periodo, caminhao_id=self.caminhao_id, motorista__iexact=self.motorista):

            valor = item.quantidade * item.valor_unitario

            if item.tipo == "receita":

                base += valor

            elif item.descricao.strip().upper() in ("AREIA", "PEDRA"):

                base -= valor

        return max(base, Decimal(0))



    @property

    def valor_comissao(self):

        if self.comissao_percentual is None:

            return self.comissao

        return (self.base_comissao * self.comissao_percentual / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

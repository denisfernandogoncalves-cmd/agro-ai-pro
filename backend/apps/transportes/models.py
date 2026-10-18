from apps.financeiro.integracao import OrigemFinanceira, dados_conta
from decimal import Decimal, ROUND_HALF_UP



from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator

from django.db import models
from django.conf import settings





class Motorista(models.Model):
    nome = models.CharField(max_length=120, unique=True)
    apelido = models.CharField(max_length=80, blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ("nome", "id")


class EmprestimoMotorista(models.Model):
    motorista = models.ForeignKey(Motorista, on_delete=models.PROTECT, related_name='emprestimos')
    nome_original = models.CharField(max_length=120)
    data = models.DateField()
    vencimento = models.DateField()
    valor = models.DecimalField(max_digits=14, decimal_places=2)
    juros_percentual = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    motivo = models.CharField(max_length=500)
    chave = models.UUIDField(unique=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    criado_em = models.DateTimeField(auto_now_add=True)

    @property
    def total(self):
        # Juros únicos sobre o principal, pactuados na contratação, sem mora automática.
        return (self.valor * (1 + self.juros_percentual / 100)).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)

    class Meta:
        ordering = ('-data', '-id')
        constraints = [models.CheckConstraint(condition=models.Q(valor__gt=0, juros_percentual__gte=0), name='emprestimo_valores_validos')]


class PagamentoEmprestimo(models.Model):
    emprestimo = models.ForeignKey(EmprestimoMotorista, on_delete=models.PROTECT, related_name='pagamentos')
    data = models.DateField()
    valor = models.DecimalField(max_digits=14, decimal_places=2)
    remuneracao = models.ForeignKey('RemuneracaoMotorista', null=True, blank=True, on_delete=models.PROTECT, related_name='pagamentos_emprestimos')
    observacao = models.CharField(max_length=500)
    chave = models.UUIDField(unique=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    criado_em = models.DateTimeField(auto_now_add=True)
    estornado_em = models.DateTimeField(null=True)
    estornado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name='+')
    motivo_estorno = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ('data', 'id')
        constraints = [models.CheckConstraint(condition=models.Q(valor__gt=0), name='pagamento_emprestimo_positivo')]


class Caminhao(models.Model):

    placa = models.CharField(max_length=7, unique=True, validators=[RegexValidator(r"^[A-Z]{3}[0-9][A-Z0-9][0-9]{2}$", "Informe uma placa brasileira válida.")])

    veiculo = models.CharField(max_length=100)

    motorista = models.CharField(max_length=120, blank=True)

    ativo = models.BooleanField(default=True)



    class Meta:

        ordering = ("placa",)





class LancamentoTransporte(OrigemFinanceira):

    def dados_conta_pagar(self):
        if self.tipo != "despesa" or self.abasteceu_silo:
            return None
        return dados_conta(f"Transporte #{self.pk} · {self.caminhao.placa} · {self.descricao}", self.total, self.data)


    abasteceu_silo = models.BooleanField(default=False)
    tipo_diesel = models.CharField(max_length=4, blank=True, choices=(("S10", "S10"), ("S500", "S500")))
    compra_diesel = models.ForeignKey("maquinas.CompraDiesel", null=True, blank=True, on_delete=models.PROTECT, related_name="abastecimentos_silo")

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





class RemuneracaoMotorista(OrigemFinanceira):

    def save(self, *args, **kwargs):
        from django.db import transaction
        from rest_framework.exceptions import ValidationError
        with transaction.atomic():
            if self.pk:
                anterior = type(self).objects.select_for_update().get(pk=self.pk)
                if self.pagamentos_emprestimos.exists() and any(getattr(self, campo) != getattr(anterior, campo) for campo in ('motorista', 'competencia', 'caminhao_id')):
                    raise ValidationError('A remuneração tem histórico de empréstimos. Preserve motorista, placa e competência.')
                self.dados_conta_pagar()  # Também protege remunerações históricas sem integração financeira.
            return super().save(*args, **kwargs)

    def dados_conta_pagar(self):
        desconto = sum((p.valor for p in self.pagamentos_emprestimos.filter(estornado_em__isnull=True)), Decimal(0)) if self.pk else Decimal(0)
        liquido = Decimal(self.salario) + self.valor_comissao - desconto
        if liquido < 0:
            from rest_framework.exceptions import ValidationError
            raise ValidationError('A remuneração não pode ficar abaixo dos empréstimos já pagos neste holerite.')
        return dados_conta(f"Remuneração #{self.pk} · {self.motorista} · {self.competencia:%m/%Y}", liquido, self.competencia, recebedor_nome=self.motorista)


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

    def valor_comissao_transporte(self):

        if self.comissao_percentual is None:

            return Decimal(str(self.comissao)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return (self.base_comissao * self.comissao_percentual / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


    @property
    def comissao_fretes(self):
        if not self.pk:
            return Decimal("0.00")
        return self.fretes_conferidos.filter(ja_contabilizado=False).filter(
            models.Q(carga__status="ativa") | models.Q(entrega__isnull=False, entrega__cancelado_em__isnull=True)
        ).aggregate(total=models.Sum("comissao"))["total"] or Decimal("0.00")

    @property
    def valor_comissao(self):
        return self.valor_comissao_transporte + self.comissao_fretes


class FreteConferido(models.Model):
    carga = models.OneToOneField("graos.CargaColhida", on_delete=models.PROTECT, null=True, blank=True, related_name="frete_conferido")
    entrega = models.OneToOneField("vendas.EntregaVendaGraos", on_delete=models.PROTECT, null=True, blank=True, related_name="frete_conferido")
    remuneracao = models.ForeignKey(RemuneracaoMotorista, on_delete=models.PROTECT, related_name="fretes_conferidos")
    frete = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    comissao = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    ja_contabilizado = models.BooleanField(default=True)
    observacoes = models.CharField(max_length=220, blank=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=(models.Q(carga__isnull=False, entrega__isnull=True) | models.Q(carga__isnull=True, entrega__isnull=False)), name="frete_origem_unica"),
            models.CheckConstraint(condition=models.Q(frete__gte=0, comissao__gte=0), name="frete_valores_nao_negativos"),
        ]

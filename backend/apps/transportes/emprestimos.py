from decimal import Decimal
from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework import serializers, viewsets, mixins
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from apps.accounts.access import verificar_acesso
from .models import EmprestimoMotorista, PagamentoEmprestimo, RemuneracaoMotorista
from apps.financeiro.integracao import sincronizar
from apps.financeiro.models import LancamentoFinanceiro


class PagamentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PagamentoEmprestimo
        fields = ('id', 'data', 'valor', 'remuneracao', 'observacao', 'chave', 'usuario', 'criado_em', 'estornado_em', 'estornado_por', 'motivo_estorno')
        read_only_fields = ('usuario', 'criado_em', 'estornado_em', 'estornado_por', 'motivo_estorno')
        extra_kwargs = {'chave': {'validators': []}, 'valor': {'min_value': Decimal('.01')}, 'observacao': {'allow_blank': False}, 'remuneracao': {'default': None}}


class EmprestimoSerializer(serializers.ModelSerializer):
    pagamentos = PagamentoSerializer(many=True, read_only=True)
    total = serializers.DecimalField(max_digits=16, decimal_places=2, read_only=True)
    saldo = serializers.SerializerMethodField()

    def get_saldo(self, obj):
        return str(obj.total - sum((p.valor for p in obj.pagamentos.all() if not p.estornado_em), Decimal(0)))

    def validate(self, data):
        if data['vencimento'] < data['data']:
            raise ValidationError('Vencimento anterior ao empréstimo.')
        if not data['motorista'].ativo:
            raise ValidationError('Selecione um motorista ativo.')
        return data

    class Meta:
        model = EmprestimoMotorista
        fields = '__all__'
        read_only_fields = ('nome_original', 'usuario', 'criado_em')
        extra_kwargs = {'chave': {'validators': []}, 'valor': {'min_value': Decimal('.01')}, 'juros_percentual': {'min_value': 0, 'max_value': 1000, 'default': Decimal(0)}, 'motivo': {'allow_blank': False}}


def mesmo_payload(obj, dados):
    return all(getattr(obj, k) == v for k, v in dados.items())


class PaginacaoEmprestimos(PageNumberPagination):
    page_size = 30


class EmprestimoViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = EmprestimoMotorista.objects.select_related('motorista').prefetch_related('pagamentos')
    serializer_class = EmprestimoSerializer
    pagination_class = PaginacaoEmprestimos

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        verificar_acesso(request.user, request.path, request.method)

    def get_queryset(self):
        qs = super().get_queryset()
        motorista = self.request.query_params.get('motorista')
        if motorista:
            if not motorista.isdigit():
                raise ValidationError('Motorista inválido.')
            qs = qs.filter(motorista_id=motorista)
        return qs

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        dados = s.validated_data
        # Serializa também duas requisições simultâneas da mesma chave/motorista.
        type(dados['motorista']).objects.select_for_update().get(pk=dados['motorista'].pk)
        existente = EmprestimoMotorista.objects.filter(chave=dados['chave']).first()
        if existente:
            if not mesmo_payload(existente, dados):
                return Response({'detail': 'Chave já utilizada com outros dados.'}, status=409)
            return Response(self.get_serializer(existente).data)
        try:
            with transaction.atomic():
                obj = s.save(nome_original=dados['motorista'].nome, usuario=request.user)
        except IntegrityError:
            return Response({'detail': 'Chave já utilizada por outra requisição. Atualize a consulta.'}, status=409)
        return Response(self.get_serializer(obj).data, status=201)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def pagamentos(self, request, pk=None):
        obj = EmprestimoMotorista.objects.select_for_update().get(pk=self.get_object().pk)
        s = PagamentoSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        dados = s.validated_data
        existente = PagamentoEmprestimo.objects.filter(chave=dados['chave']).first()
        if existente:
            if existente.emprestimo_id != obj.pk or not mesmo_payload(existente, dados):
                return Response({'detail': 'Chave já utilizada com outros dados.'}, status=409)
            return Response(PagamentoSerializer(existente).data)
        if dados['data'] < obj.data or dados['data'] > timezone.localdate():
            raise ValidationError('Pagamento deve ocorrer entre a data do empréstimo e hoje. Use vencimento para previsão.')
        pago = obj.pagamentos.filter(estornado_em__isnull=True).aggregate(v=Sum('valor'))['v'] or Decimal(0)
        if dados['valor'] > obj.total - pago:
            raise ValidationError('Pagamento excede o saldo devedor.')
        rem = dados.get('remuneracao')
        if rem:
            rem = RemuneracaoMotorista.objects.select_for_update().get(pk=rem.pk)
            if rem.motorista != obj.nome_original:
                raise ValidationError('A remuneração escolhida não corresponde ao nome original exato deste motorista. Nenhum vínculo por aproximação é permitido.')
            mes = rem.competencia
            if (dados['data'].year, dados['data'].month) != (mes.year, mes.month):
                raise ValidationError('A data do pagamento deve pertencer à competência do holerite escolhido.')
            if rem.conta_pagar_id:
                conta = LancamentoFinanceiro.objects.select_for_update().get(pk=rem.conta_pagar_id)
                if conta.status != 'pendente':
                    raise ValidationError('O título da remuneração já foi liquidado ou cancelado. Confira-o no Financeiro antes de descontar empréstimos.')
            # Limite por registro explícito: não usa outras placas como crédito implícito.
            descontos = rem.pagamentos_emprestimos.filter(estornado_em__isnull=True).aggregate(v=Sum('valor'))['v'] or Decimal(0)
            if descontos + dados['valor'] > rem.salario + rem.valor_comissao:
                raise ValidationError('Desconto excede o valor da remuneração selecionada.')
        try:
            with transaction.atomic():
                pagamento = s.save(emprestimo=obj, usuario=request.user)
        except IntegrityError:
            return Response({'detail': 'Chave já utilizada por outra requisição. Atualize a consulta.'}, status=409)
        if rem:
            sincronizar(rem)
        return Response(PagamentoSerializer(pagamento).data, status=201)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def estornar(self, request, pk=None):
        obj = EmprestimoMotorista.objects.select_for_update().get(pk=self.get_object().pk)
        try:
            pagamento = obj.pagamentos.select_for_update().get(pk=request.data.get('pagamento'))
        except (PagamentoEmprestimo.DoesNotExist, ValueError, TypeError):
            raise ValidationError('Pagamento não encontrado neste empréstimo.')
        motivo = request.data.get('motivo', '')
        if not isinstance(motivo, str) or not motivo.strip() or len(motivo) > 500:
            raise ValidationError('Informe a justificativa do estorno (até 500 caracteres).')
        if not pagamento.estornado_em:
            rem = None
            if pagamento.remuneracao_id:
                rem = RemuneracaoMotorista.objects.select_for_update().get(pk=pagamento.remuneracao_id)
                if rem.conta_pagar_id:
                    conta = LancamentoFinanceiro.objects.select_for_update().get(pk=rem.conta_pagar_id)
                    if conta.status == 'liquidado':
                        raise ValidationError('A remuneração está liquidada. Confira a baixa no Financeiro antes do estorno.')
                    if conta.status == 'cancelado':
                        # Só reabre o título zerado pelos descontos; cancelamentos independentes ficam protegidos.
                        if rem.dados_conta_pagar()['valor'] != 0:
                            raise ValidationError('O título foi cancelado independentemente do empréstimo. Confira no Financeiro.')
                        conta.status = 'pendente'
                        conta.save(update_fields=['status', 'atualizado_em'])
            pagamento.estornado_em = timezone.now()
            pagamento.estornado_por = request.user
            pagamento.motivo_estorno = motivo.strip()
            pagamento.save(update_fields=['estornado_em', 'estornado_por', 'motivo_estorno'])
            if rem:
                sincronizar(rem)
        return Response(PagamentoSerializer(pagamento).data)

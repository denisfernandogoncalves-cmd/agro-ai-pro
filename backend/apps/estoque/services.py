from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Case, DecimalField, F, Q, Sum, Value, When
from django.db.models.functions import Coalesce
from django.utils import timezone

from .models import LoteEstoque, MovimentacaoEstoque, ProdutoEstoque


class EstoqueInsuficienteError(ValueError):
    pass


def saldo_lote(lote):
    agregado = lote.movimentacoes.aggregate(
        saldo=Coalesce(
            Sum(
                Case(
                    When(tipo=MovimentacaoEstoque.Tipo.ENTRADA, then=F("quantidade")),
                    default=-F("quantidade"),
                    output_field=DecimalField(max_digits=14, decimal_places=3),
                )
            ),
            Value(Decimal("0")),
            output_field=DecimalField(max_digits=14, decimal_places=3),
        )
    )
    return agregado["saldo"]


@transaction.atomic
def registrar_movimentacao(*, usuario, **dados):
    lote_enviado = dados.pop("lote")
    lote = LoteEstoque.objects.select_for_update().select_related("produto").get(
        pk=lote_enviado.pk
    )
    try:
        quantidade = Decimal(str(dados["quantidade"]))
    except (InvalidOperation, TypeError) as exc:
        raise ValueError("Quantidade inválida.") from exc
    if quantidade <= 0:
        raise ValueError("A quantidade deve ser maior que zero.")
    if not lote.ativo or not lote.produto.ativo:
        raise ValueError("O lote e o produto precisam estar ativos.")
    if dados["tipo"] == MovimentacaoEstoque.Tipo.SAIDA:
        saldo = saldo_lote(lote)
        if quantidade > saldo:
            raise EstoqueInsuficienteError(
                f"Saldo insuficiente. Disponível: {saldo} {lote.produto.unidade}."
            )
    movimento = MovimentacaoEstoque(lote=lote, criado_por=usuario, **dados)
    movimento.full_clean()
    movimento.save()
    return movimento


def _lotes_no_escopo(queryset=None, *, propriedade=None, safra=""):
    lotes = queryset if queryset is not None else LoteEstoque.objects.all()
    lotes = lotes.select_related("produto", "local")
    if propriedade:
        lotes = lotes.filter(local__propriedade_id=propriedade)
    if safra:
        lotes = lotes.filter(movimentacoes__safra=safra)
    return lotes.distinct()


def posicao_estoque(queryset=None, *, propriedade=None, safra=""):
    lotes = _lotes_no_escopo(
        queryset,
        propriedade=propriedade,
        safra=safra,
    )
    filtro_safra = Q()
    if safra:
        filtro_safra &= Q(movimentacoes__safra=safra)

    campo_decimal = DecimalField(max_digits=14, decimal_places=3)
    lotes = lotes.annotate(
        total_entradas=Coalesce(
            Sum(
                "movimentacoes__quantidade",
                filter=(
                    filtro_safra
                    & Q(movimentacoes__tipo=MovimentacaoEstoque.Tipo.ENTRADA)
                ),
            ),
            Value(Decimal("0")),
            output_field=campo_decimal,
        ),
        total_saidas=Coalesce(
            Sum(
                "movimentacoes__quantidade",
                filter=(
                    filtro_safra
                    & Q(movimentacoes__tipo=MovimentacaoEstoque.Tipo.SAIDA)
                ),
            ),
            Value(Decimal("0")),
            output_field=campo_decimal,
        ),
    )

    resultado = []
    hoje = timezone.localdate()
    for lote in lotes:
        saldo = lote.total_entradas - lote.total_saidas
        if saldo == 0 and not lote.ativo:
            continue
        resultado.append(
            {
                "lote_id": lote.id,
                "produto_id": lote.produto_id,
                "produto": lote.produto.nome,
                "categoria": lote.produto.categoria,
                "unidade": lote.produto.unidade,
                "local_id": lote.local_id,
                "local": lote.local.nome,
                "codigo_lote": lote.codigo,
                "data_validade": lote.data_validade,
                "vencido": bool(lote.data_validade and lote.data_validade < hoje),
                "vence_em_30_dias": bool(
                    lote.data_validade
                    and hoje <= lote.data_validade <= hoje + timedelta(days=30)
                ),
                "saldo": saldo,
                "abaixo_minimo": saldo < lote.produto.estoque_minimo,
            }
        )
    return resultado


def resumo_estoque(queryset=None, *, propriedade=None, safra=""):
    lotes = _lotes_no_escopo(
        queryset,
        propriedade=propriedade,
        safra=safra,
    )
    posicoes = posicao_estoque(lotes, safra=safra)

    produtos_ativos = ProdutoEstoque.objects.filter(ativo=True)
    if queryset is not None or propriedade or safra:
        produtos_ativos = produtos_ativos.filter(lotes__in=lotes).distinct()

    return {
        "produtos_ativos": produtos_ativos.count(),
        "lotes_com_saldo": sum(1 for item in posicoes if item["saldo"] > 0),
        "lotes_vencidos": sum(
            1 for item in posicoes if item["saldo"] > 0 and item["vencido"]
        ),
        "lotes_vencendo": sum(
            1 for item in posicoes if item["saldo"] > 0 and item["vence_em_30_dias"]
        ),
        "itens_abaixo_minimo": sum(
            1 for item in posicoes if item["abaixo_minimo"]
        ),
    }

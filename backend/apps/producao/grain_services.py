from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Sum

from apps.financeiro.models import CategoriaFinanceira, LancamentoFinanceiro

from .grain_access import exigir_acesso_cadpro
from .grain_models import (
    AuditoriaProducao,
    EmbarqueProducao,
    MovimentacaoGraos,
    RecebimentoProducao,
    SaldoGraos,
)


class ProducaoError(Exception):
    pass


def _quantizar(valor, casas="0.001"):
    return Decimal(str(valor)).quantize(Decimal(casas), rounding=ROUND_HALF_UP)


def _valor_auditavel(valor):
    if isinstance(valor, Decimal):
        return str(valor)
    if hasattr(valor, "isoformat"):
        return valor.isoformat()
    if isinstance(valor, (str, int, float, bool, list, dict, type(None))):
        return valor
    return str(valor)


def _dados_auditoria(objeto):
    return {
        campo.name: _valor_auditavel(getattr(objeto, campo.attname))
        for campo in objeto._meta.concrete_fields
    }


def registrar_auditoria(*, usuario, acao, objeto, anteriores=None, metadados=None):
    propriedade = getattr(objeto, "propriedade", None)
    return AuditoriaProducao.objects.create(
        propriedade=propriedade,
        usuario=usuario,
        acao=acao,
        entidade=objeto._meta.label,
        entidade_id=objeto.pk,
        dados_anteriores=anteriores or {},
        dados_novos=_dados_auditoria(objeto),
        metadados=metadados or {},
    )


def _saldo_kwargs(*, propriedade, cadpro, talhao, cultura, safra, local):
    return {
        "propriedade": propriedade,
        "cadpro": cadpro,
        "talhao": talhao,
        "cultura": cultura,
        "safra": safra,
        "local_armazenagem": local,
    }


def _obter_saldo_bloqueado(**kwargs):
    saldo, _ = SaldoGraos.objects.select_for_update().get_or_create(
        **kwargs,
        defaults={"quantidade_kg": Decimal("0")},
    )
    return saldo


def _creditar(*, quantidade, **kwargs):
    saldo = _obter_saldo_bloqueado(**kwargs)
    saldo.quantidade_kg = _quantizar(saldo.quantidade_kg + quantidade)
    saldo.full_clean()
    saldo.save(update_fields=("quantidade_kg", "atualizado_em"))
    return saldo


def _debitar(*, quantidade, **kwargs):
    saldo = _obter_saldo_bloqueado(**kwargs)
    novo_saldo = _quantizar(saldo.quantidade_kg - quantidade)
    if novo_saldo < 0:
        raise ProducaoError(
            f"Saldo insuficiente. Disponível: {saldo.quantidade_kg} kg; solicitado: {quantidade} kg."
        )
    saldo.quantidade_kg = novo_saldo
    saldo.full_clean()
    saldo.save(update_fields=("quantidade_kg", "atualizado_em"))
    return saldo


@transaction.atomic
def registrar_movimentacao(
    *,
    usuario,
    tipo,
    propriedade,
    cadpro,
    cultura,
    safra,
    quantidade_kg,
    talhao=None,
    local_origem=None,
    local_destino=None,
    referencia_tipo="",
    referencia_id=None,
    motivo="",
    estorno_de=None,
):
    exigir_acesso_cadpro(usuario, cadpro)
    quantidade = _quantizar(quantidade_kg)
    if quantidade <= 0:
        raise ProducaoError("A quantidade deve ser positiva.")

    movimento = MovimentacaoGraos(
        tipo=tipo,
        propriedade=propriedade,
        cadpro=cadpro,
        talhao=talhao,
        cultura=cultura,
        safra=safra,
        local_origem=local_origem,
        local_destino=local_destino,
        quantidade_kg=quantidade,
        referencia_tipo=referencia_tipo,
        referencia_id=referencia_id,
        motivo=motivo,
        estorno_de=estorno_de,
        criado_por=usuario,
    )
    movimento.full_clean()

    base = {
        "propriedade": propriedade,
        "cadpro": cadpro,
        "talhao": talhao,
        "cultura": cultura,
        "safra": safra,
    }
    if tipo in {MovimentacaoGraos.Tipo.ENTRADA, MovimentacaoGraos.Tipo.AJUSTE_ENTRADA}:
        _creditar(quantidade=quantidade, **_saldo_kwargs(local=local_destino, **base))
    elif tipo in {MovimentacaoGraos.Tipo.SAIDA, MovimentacaoGraos.Tipo.AJUSTE_SAIDA}:
        _debitar(quantidade=quantidade, **_saldo_kwargs(local=local_origem, **base))
    elif tipo == MovimentacaoGraos.Tipo.TRANSFERENCIA:
        _debitar(quantidade=quantidade, **_saldo_kwargs(local=local_origem, **base))
        _creditar(quantidade=quantidade, **_saldo_kwargs(local=local_destino, **base))
    elif tipo == MovimentacaoGraos.Tipo.ESTORNO:
        if not estorno_de:
            raise ProducaoError("Informe a movimentação que será estornada.")
        if hasattr(estorno_de, "estorno"):
            raise ProducaoError("Esta movimentação já foi estornada.")
        if estorno_de.tipo in {MovimentacaoGraos.Tipo.ENTRADA, MovimentacaoGraos.Tipo.AJUSTE_ENTRADA}:
            _debitar(quantidade=quantidade, **_saldo_kwargs(local=estorno_de.local_destino, **base))
        elif estorno_de.tipo in {MovimentacaoGraos.Tipo.SAIDA, MovimentacaoGraos.Tipo.AJUSTE_SAIDA}:
            _creditar(quantidade=quantidade, **_saldo_kwargs(local=estorno_de.local_origem, **base))
        elif estorno_de.tipo == MovimentacaoGraos.Tipo.TRANSFERENCIA:
            _debitar(quantidade=quantidade, **_saldo_kwargs(local=estorno_de.local_destino, **base))
            _creditar(quantidade=quantidade, **_saldo_kwargs(local=estorno_de.local_origem, **base))
        else:
            raise ProducaoError("Movimentações de estorno não podem ser estornadas novamente.")

    movimento.save()
    registrar_auditoria(usuario=usuario, acao="movimentacao_criada", objeto=movimento)
    return movimento


@transaction.atomic
def confirmar_recebimento(recebimento, *, usuario):
    recebimento = RecebimentoProducao.objects.select_for_update().select_related(
        "cadpro__propriedade",
        "cultura",
        "safra",
        "talhao",
        "local_armazenagem",
    ).get(pk=recebimento.pk)
    exigir_acesso_cadpro(usuario, recebimento.cadpro)
    if recebimento.status != RecebimentoProducao.Status.RASCUNHO:
        raise ProducaoError("Somente recebimentos em rascunho podem ser confirmados.")
    recebimento.full_clean()
    recebimento.quantidade_sacas = _quantizar(
        recebimento.peso_liquido_kg / recebimento.cultura.peso_saca_kg
    )
    movimento = registrar_movimentacao(
        usuario=usuario,
        tipo=MovimentacaoGraos.Tipo.ENTRADA,
        propriedade=recebimento.propriedade,
        cadpro=recebimento.cadpro,
        talhao=recebimento.talhao,
        cultura=recebimento.cultura,
        safra=recebimento.safra,
        quantidade_kg=recebimento.peso_liquido_kg,
        local_destino=recebimento.local_armazenagem,
        referencia_tipo="recebimento",
        referencia_id=recebimento.pk,
    )
    anteriores = _dados_auditoria(recebimento)
    recebimento.movimentacao = movimento
    recebimento.status = RecebimentoProducao.Status.CONFIRMADO
    recebimento.save(update_fields=("quantidade_sacas", "movimentacao", "status", "atualizado_em"))
    registrar_auditoria(
        usuario=usuario,
        acao="recebimento_confirmado",
        objeto=recebimento,
        anteriores=anteriores,
    )
    return recebimento


@transaction.atomic
def estornar_recebimento(recebimento, *, usuario, motivo):
    recebimento = RecebimentoProducao.objects.select_for_update().select_related(
        "cadpro__propriedade", "movimentacao"
    ).get(pk=recebimento.pk)
    exigir_acesso_cadpro(usuario, recebimento.cadpro)
    if recebimento.status != RecebimentoProducao.Status.CONFIRMADO or not recebimento.movimentacao:
        raise ProducaoError("Somente recebimentos confirmados podem ser estornados.")
    movimento = registrar_movimentacao(
        usuario=usuario,
        tipo=MovimentacaoGraos.Tipo.ESTORNO,
        propriedade=recebimento.propriedade,
        cadpro=recebimento.cadpro,
        talhao=recebimento.talhao,
        cultura=recebimento.cultura,
        safra=recebimento.safra,
        quantidade_kg=recebimento.peso_liquido_kg,
        local_origem=recebimento.local_armazenagem,
        estorno_de=recebimento.movimentacao,
        referencia_tipo="recebimento",
        referencia_id=recebimento.pk,
        motivo=motivo,
    )
    anteriores = _dados_auditoria(recebimento)
    recebimento.status = RecebimentoProducao.Status.ESTORNADO
    recebimento.save(update_fields=("status", "atualizado_em"))
    registrar_auditoria(
        usuario=usuario,
        acao="recebimento_estornado",
        objeto=recebimento,
        anteriores=anteriores,
        metadados={"movimentacao_estorno": movimento.pk, "motivo": motivo},
    )
    return recebimento


def _quantidade_embarcada_contrato(contrato):
    return contrato.embarques.filter(status=EmbarqueProducao.Status.CONFIRMADO).aggregate(
        total=Sum("quantidade_kg")
    )["total"] or Decimal("0")


@transaction.atomic
def confirmar_embarque(embarque, *, usuario):
    embarque = EmbarqueProducao.objects.select_for_update().select_related(
        "cadpro__propriedade",
        "cultura",
        "safra",
        "contrato",
        "comprador",
        "local_armazenagem",
    ).get(pk=embarque.pk)
    exigir_acesso_cadpro(usuario, embarque.cadpro)
    if embarque.status != EmbarqueProducao.Status.RASCUNHO:
        raise ProducaoError("Somente embarques em rascunho podem ser confirmados.")
    embarque.full_clean()
    if embarque.contrato:
        contrato = type(embarque.contrato).objects.select_for_update().get(pk=embarque.contrato_id)
        embarcado = _quantidade_embarcada_contrato(contrato)
        limite = contrato.quantidade_kg * (
            Decimal("1") + contrato.tolerancia_percentual / Decimal("100")
        )
        if embarcado + embarque.quantidade_kg > limite:
            raise ProducaoError("O embarque supera o saldo permitido do contrato.")

    embarque.quantidade_sacas = _quantizar(
        embarque.quantidade_kg / embarque.cultura.peso_saca_kg
    )
    embarque.valor_total = (embarque.quantidade_sacas * embarque.preco_saca).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    movimento = registrar_movimentacao(
        usuario=usuario,
        tipo=MovimentacaoGraos.Tipo.SAIDA,
        propriedade=embarque.propriedade,
        cadpro=embarque.cadpro,
        cultura=embarque.cultura,
        safra=embarque.safra,
        quantidade_kg=embarque.quantidade_kg,
        local_origem=embarque.local_armazenagem,
        referencia_tipo="embarque",
        referencia_id=embarque.pk,
    )
    categoria, _ = CategoriaFinanceira.objects.get_or_create(
        nome="Venda de produção agrícola",
        defaults={"aplicacao": CategoriaFinanceira.Aplicacao.RECEITA},
    )
    vencimento = embarque.contrato.data_limite if embarque.contrato and embarque.contrato.data_limite else embarque.data.date()
    lancamento = LancamentoFinanceiro.objects.create(
        tipo=LancamentoFinanceiro.Tipo.RECEBER,
        descricao=f"Venda de {embarque.cultura.nome} - romaneio {embarque.romaneio}",
        valor=embarque.valor_total,
        categoria=categoria,
        parceiro=embarque.comprador,
        propriedade=embarque.propriedade,
        safra=embarque.safra.nome,
        data_emissao=embarque.data.date(),
        data_vencimento=vencimento,
        observacoes=f"Gerado automaticamente pelo embarque {embarque.pk}.",
    )
    anteriores = _dados_auditoria(embarque)
    embarque.movimentacao = movimento
    embarque.lancamento_financeiro = lancamento
    embarque.status = EmbarqueProducao.Status.CONFIRMADO
    embarque.save(
        update_fields=(
            "quantidade_sacas",
            "valor_total",
            "movimentacao",
            "lancamento_financeiro",
            "status",
            "atualizado_em",
        )
    )
    registrar_auditoria(
        usuario=usuario,
        acao="embarque_confirmado",
        objeto=embarque,
        anteriores=anteriores,
        metadados={"lancamento_financeiro": lancamento.pk},
    )
    return embarque


@transaction.atomic
def estornar_embarque(embarque, *, usuario, motivo):
    embarque = EmbarqueProducao.objects.select_for_update().select_related(
        "cadpro__propriedade", "movimentacao", "lancamento_financeiro"
    ).get(pk=embarque.pk)
    exigir_acesso_cadpro(usuario, embarque.cadpro)
    if embarque.status != EmbarqueProducao.Status.CONFIRMADO or not embarque.movimentacao:
        raise ProducaoError("Somente embarques confirmados podem ser estornados.")
    movimento = registrar_movimentacao(
        usuario=usuario,
        tipo=MovimentacaoGraos.Tipo.ESTORNO,
        propriedade=embarque.propriedade,
        cadpro=embarque.cadpro,
        cultura=embarque.cultura,
        safra=embarque.safra,
        quantidade_kg=embarque.quantidade_kg,
        local_destino=embarque.local_armazenagem,
        estorno_de=embarque.movimentacao,
        referencia_tipo="embarque",
        referencia_id=embarque.pk,
        motivo=motivo,
    )
    anteriores = _dados_auditoria(embarque)
    if embarque.lancamento_financeiro and embarque.lancamento_financeiro.status == LancamentoFinanceiro.Status.PENDENTE:
        embarque.lancamento_financeiro.status = LancamentoFinanceiro.Status.CANCELADO
        embarque.lancamento_financeiro.observacoes = (
            f"{embarque.lancamento_financeiro.observacoes}\nCancelado por estorno do embarque {embarque.pk}: {motivo}"
        ).strip()
        embarque.lancamento_financeiro.save(update_fields=("status", "observacoes", "atualizado_em"))
    embarque.status = EmbarqueProducao.Status.ESTORNADO
    embarque.save(update_fields=("status", "atualizado_em"))
    registrar_auditoria(
        usuario=usuario,
        acao="embarque_estornado",
        objeto=embarque,
        anteriores=anteriores,
        metadados={"movimentacao_estorno": movimento.pk, "motivo": motivo},
    )
    return embarque

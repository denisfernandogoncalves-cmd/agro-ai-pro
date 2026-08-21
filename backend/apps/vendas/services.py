import hashlib
import json
from datetime import date
from decimal import Decimal, InvalidOperation

from django.db import IntegrityError, transaction
from django.db.models import Count
from django.utils import timezone

from apps.graos.models import (
    LoteGraos,
    MovimentacaoGraos,
    OrigemSaldoGraos,
    PosicaoSaldoGraos,
    ReservaSaldoGraos,
)
from apps.graos.services import (
    confirmar_entrega,
    liberar_reserva,
    registrar_devolucao,
    reservar_saldo,
)

from .models import DevolucaoVendaGraos, EntregaVendaGraos, VendaGraos, ZERO


class VendaGraosError(ValueError):
    codigo = "venda_invalida"


class VendaGraosConflitoError(VendaGraosError):
    codigo = "conflito"


def _quantidade(valor):
    try:
        quantidade = Decimal(str(valor)).quantize(Decimal("0.001"))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise VendaGraosError("Informe uma quantidade válida.") from exc
    if quantidade <= ZERO:
        raise VendaGraosError("A quantidade deve ser maior que zero.")
    return quantidade


def _chave(valor):
    chave = str(valor or "").strip()
    if not chave:
        raise VendaGraosError("Informe o cabeçalho Idempotency-Key.")
    if len(chave) > 120:
        raise VendaGraosError("Idempotency-Key deve possuir no máximo 120 caracteres.")
    return chave


def _normalizar(valor):
    if isinstance(valor, (date, Decimal)):
        return str(valor)
    if hasattr(valor, "pk"):
        return str(valor.pk)
    return valor


def _hash(payload):
    canonico = {chave: _normalizar(valor) for chave, valor in payload.items()}
    return hashlib.sha256(
        json.dumps(canonico, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _validar_repeticao(hash_existente, hash_recebido):
    if hash_existente != hash_recebido:
        raise VendaGraosConflitoError(
            "A Idempotency-Key já foi usada com dados diferentes."
        )


def _repeticao_movimento(modelo, *, chave, hash_requisicao, venda_id):
    existente = modelo.objects.select_related("venda").filter(
        chave_idempotencia=chave
    ).first()
    if not existente:
        return None
    _validar_repeticao(existente.hash_requisicao, hash_requisicao)
    if existente.venda_id != venda_id:
        raise VendaGraosConflitoError("A Idempotency-Key pertence a outra venda.")
    return existente


def _lote_operacional(posicao):
    lote = (
        LoteGraos.objects.filter(
            cad_pro_id=posicao.cad_pro_id,
            cultura=posicao.cultura,
            safra=posicao.safra,
            classificacao_codigo=posicao.classificacao_codigo,
            armazem_id=posicao.armazem_id,
            ativo=True,
        )
        .annotate(total_cargas=Count("cargas_colhidas"))
        .order_by("-total_cargas", "id")
        .first()
    )
    if not lote:
        raise VendaGraosError(
            "A posição não possui lote ativo rastreável para movimentação."
        )
    return lote


def _resultado_ledger(resultado):
    origem = OrigemSaldoGraos.objects.get(pk=resultado.origem.id)
    movimento = MovimentacaoGraos.objects.get(pk=resultado.movimentacoes[0].id)
    return origem, movimento


@transaction.atomic
def criar_rascunho(
    *, usuario, posicao, numero_contrato, cliente_nome, quantidade_kg,
    chave_idempotencia, data_contrato=None, data_limite_entrega=None,
    observacoes="",
):
    chave = _chave(chave_idempotencia)
    quantidade = _quantidade(quantidade_kg)
    payload = {
        "posicao": posicao,
        "numero_contrato": str(numero_contrato).strip(),
        "cliente_nome": str(cliente_nome).strip(),
        "quantidade_kg": quantidade,
        "data_contrato": data_contrato or timezone.localdate(),
        "data_limite_entrega": data_limite_entrega,
        "observacoes": str(observacoes or "").strip(),
    }
    hash_requisicao = _hash(payload)
    existente = VendaGraos.objects.select_related("reserva").filter(
        chave_criacao=chave
    ).first()
    if existente:
        _validar_repeticao(existente.hash_criacao, hash_requisicao)
        return existente
    posicao = PosicaoSaldoGraos.objects.select_related(
        "cad_pro", "armazem", "armazem__propriedade"
    ).get(pk=posicao.pk)
    if not posicao.cad_pro.ativo or not posicao.armazem.ativo:
        raise VendaGraosError("A posição deve possuir CAD/PRO e armazenagem ativos.")
    if not payload["numero_contrato"] or not payload["cliente_nome"]:
        raise VendaGraosError("Informe contrato e cliente.")
    lote = _lote_operacional(posicao)
    try:
        venda = VendaGraos.objects.create(
            **payload,
            lote=lote,
            chave_criacao=chave,
            hash_criacao=hash_requisicao,
            criado_por=usuario,
        )
    except IntegrityError as exc:
        raise VendaGraosConflitoError(
            "O contrato ou a Idempotency-Key já está em uso."
        ) from exc
    return venda


@transaction.atomic
def confirmar_venda(*, usuario, venda, chave_idempotencia):
    chave = _chave(chave_idempotencia)
    venda = VendaGraos.objects.select_for_update().get(pk=venda.pk)
    venda.lote = LoteGraos.objects.get(pk=venda.lote_id)
    venda.posicao = PosicaoSaldoGraos.objects.get(pk=venda.posicao_id)
    hash_requisicao = _hash({"venda": venda.pk})
    if venda.chave_confirmacao == chave:
        _validar_repeticao(venda.hash_confirmacao, hash_requisicao)
        return venda
    if venda.status != VendaGraos.Status.RASCUNHO:
        raise VendaGraosConflitoError("Somente uma venda em rascunho pode ser confirmada.")
    resultado = reservar_saldo(
        usuario=usuario,
        lote=venda.lote,
        quantidade_kg=venda.quantidade_kg,
        chave_idempotencia=f"vendas:confirmar:{chave}",
        referencia_externa=venda.numero_contrato,
        observacoes=f"Reserva da venda {venda.numero_contrato}.",
        metadados={"venda_id": venda.pk, "numero_contrato": venda.numero_contrato},
    )
    venda.reserva = ReservaSaldoGraos.objects.get(pk=resultado.reserva.id)
    venda.status = VendaGraos.Status.CONFIRMADA
    venda.chave_confirmacao = chave
    venda.hash_confirmacao = hash_requisicao
    venda.confirmado_em = timezone.now()
    venda.save(update_fields=(
        "reserva", "status", "chave_confirmacao", "hash_confirmacao",
        "confirmado_em", "atualizado_em",
    ))
    return venda


@transaction.atomic
def cancelar_venda(*, usuario, venda, chave_idempotencia, observacoes=""):
    chave = _chave(chave_idempotencia)
    venda = VendaGraos.objects.select_for_update().get(pk=venda.pk)
    venda.posicao = PosicaoSaldoGraos.objects.get(pk=venda.posicao_id)
    venda.lote = LoteGraos.objects.get(pk=venda.lote_id)
    if venda.reserva_id:
        venda.reserva = ReservaSaldoGraos.objects.get(pk=venda.reserva_id)
    hash_requisicao = _hash(
        {"venda": venda.pk, "observacoes": str(observacoes or "").strip()}
    )
    if venda.chave_cancelamento == chave:
        _validar_repeticao(venda.hash_cancelamento, hash_requisicao)
        return venda
    if venda.status == VendaGraos.Status.RASCUNHO:
        venda.quantidade_cancelada_kg = venda.quantidade_kg
    elif venda.status in (VendaGraos.Status.CONFIRMADA, VendaGraos.Status.PARCIAL):
        quantidade_aberta = venda.reserva.saldo_reservado_kg
        if quantidade_aberta > ZERO:
            liberar_reserva(
                usuario=usuario,
                reserva=venda.reserva,
                quantidade_kg=quantidade_aberta,
                chave_idempotencia=f"vendas:cancelar:{chave}",
                referencia_externa=venda.numero_contrato,
                observacoes=str(observacoes or "").strip(),
                metadados={"venda_id": venda.pk},
            )
        venda.quantidade_cancelada_kg = venda.quantidade_kg - venda.quantidade_entregue_kg
    else:
        raise VendaGraosConflitoError("A venda não possui quantidade aberta para cancelamento.")
    venda.status = VendaGraos.Status.CANCELADA
    venda.chave_cancelamento = chave
    venda.hash_cancelamento = hash_requisicao
    venda.cancelado_em = timezone.now()
    venda.save(update_fields=(
        "quantidade_cancelada_kg", "status", "chave_cancelamento",
        "hash_cancelamento", "cancelado_em", "atualizado_em",
    ))
    return venda


@transaction.atomic
def registrar_entrega_venda(
    *, usuario, venda, quantidade_kg, chave_idempotencia,
    data_entrega=None, referencia_externa="", observacoes="", destino="",
    placa="", nota_produtor="", nota_empresa="",
):
    from apps.graos.models import normalizar_placa

    chave = _chave(chave_idempotencia)
    quantidade = _quantidade(quantidade_kg)
    placa_normalizada = normalizar_placa(placa)
    if placa_normalizada and len(placa_normalizada) != 7:
        raise VendaGraosConflitoError(
            "Informe uma placa brasileira com 7 letras e números."
        )
    payload = {
        "venda_id": venda.pk,
        "quantidade_kg": quantidade,
        "data_entrega": data_entrega or timezone.localdate(),
        "referencia_externa": str(referencia_externa or "").strip(),
        "observacoes": str(observacoes or "").strip(),
        "destino": str(destino or venda.cliente_nome).strip(),
        "placa": placa_normalizada,
        "nota_produtor": str(nota_produtor or "").strip(),
        "nota_empresa": str(nota_empresa or "").strip(),
    }
    hash_requisicao = _hash(payload)
    existente = _repeticao_movimento(
        EntregaVendaGraos, chave=chave, hash_requisicao=hash_requisicao,
        venda_id=venda.pk,
    )
    if existente:
        return existente
    venda = VendaGraos.objects.select_for_update().get(pk=venda.pk)
    existente = _repeticao_movimento(
        EntregaVendaGraos, chave=chave, hash_requisicao=hash_requisicao,
        venda_id=venda.pk,
    )
    if existente:
        return existente
    venda.reserva = ReservaSaldoGraos.objects.get(pk=venda.reserva_id)
    venda.lote = LoteGraos.objects.get(pk=venda.lote_id)
    venda.posicao = PosicaoSaldoGraos.objects.get(pk=venda.posicao_id)
    if venda.status not in (VendaGraos.Status.CONFIRMADA, VendaGraos.Status.PARCIAL):
        raise VendaGraosConflitoError("A venda não está aberta para entrega.")
    if quantidade > venda.reserva.saldo_reservado_kg:
        raise VendaGraosConflitoError("A entrega excede a reserva aberta da venda.")
    resultado = confirmar_entrega(
        usuario=usuario,
        reserva=venda.reserva,
        quantidade_kg=quantidade,
        chave_idempotencia=f"vendas:entrega:{chave}",
        data_movimento=payload["data_entrega"],
        referencia_externa=payload["referencia_externa"] or venda.numero_contrato,
        observacoes=payload["observacoes"],
        metadados={"venda_id": venda.pk},
    )
    origem, movimento = _resultado_ledger(resultado)
    entrega = EntregaVendaGraos.objects.create(
        venda=venda,
        quantidade_kg=payload["quantidade_kg"],
        data_entrega=payload["data_entrega"],
        referencia_externa=payload["referencia_externa"],
        destino=payload["destino"],
        placa=payload["placa"],
        nota_produtor=payload["nota_produtor"],
        nota_empresa=payload["nota_empresa"],
        observacoes=payload["observacoes"],
        chave_idempotencia=chave,
        hash_requisicao=hash_requisicao,
        origem=origem,
        movimentacao=movimento,
        criado_por=usuario,
    )
    venda.quantidade_entregue_kg += quantidade
    venda.status = (
        VendaGraos.Status.ENTREGUE
        if venda.quantidade_entregue_kg == venda.quantidade_kg
        else VendaGraos.Status.PARCIAL
    )
    venda.save(update_fields=("quantidade_entregue_kg", "status", "atualizado_em"))
    return entrega


@transaction.atomic
def registrar_devolucao_venda(
    *, usuario, venda, quantidade_kg, chave_idempotencia,
    data_devolucao=None, referencia_externa="", observacoes="",
):
    chave = _chave(chave_idempotencia)
    quantidade = _quantidade(quantidade_kg)
    payload = {
        "venda_id": venda.pk,
        "quantidade_kg": quantidade,
        "data_devolucao": data_devolucao or timezone.localdate(),
        "referencia_externa": str(referencia_externa or "").strip(),
        "observacoes": str(observacoes or "").strip(),
    }
    hash_requisicao = _hash(payload)
    existente = _repeticao_movimento(
        DevolucaoVendaGraos, chave=chave, hash_requisicao=hash_requisicao,
        venda_id=venda.pk,
    )
    if existente:
        return existente
    venda = VendaGraos.objects.select_for_update().get(pk=venda.pk)
    existente = _repeticao_movimento(
        DevolucaoVendaGraos, chave=chave, hash_requisicao=hash_requisicao,
        venda_id=venda.pk,
    )
    if existente:
        return existente
    venda.lote = LoteGraos.objects.get(pk=venda.lote_id)
    venda.posicao = PosicaoSaldoGraos.objects.get(pk=venda.posicao_id)
    if venda.reserva_id:
        venda.reserva = ReservaSaldoGraos.objects.get(pk=venda.reserva_id)
    devolvivel = venda.quantidade_entregue_kg - venda.quantidade_devolvida_kg
    if quantidade > devolvivel:
        raise VendaGraosConflitoError(
            f"A devolução excede {devolvivel} kg entregues ainda não devolvidos."
        )
    resultado = registrar_devolucao(
        usuario=usuario,
        lote=venda.lote,
        quantidade_kg=quantidade,
        chave_idempotencia=f"vendas:devolucao:{chave}",
        data_movimento=payload["data_devolucao"],
        referencia_externa=payload["referencia_externa"] or venda.numero_contrato,
        observacoes=payload["observacoes"],
        metadados={"venda_id": venda.pk},
    )
    origem, movimento = _resultado_ledger(resultado)
    devolucao = DevolucaoVendaGraos.objects.create(
        venda=venda,
        quantidade_kg=payload["quantidade_kg"],
        data_devolucao=payload["data_devolucao"],
        referencia_externa=payload["referencia_externa"],
        observacoes=payload["observacoes"],
        chave_idempotencia=chave,
        hash_requisicao=hash_requisicao,
        origem=origem,
        movimentacao=movimento,
        criado_por=usuario,
    )
    venda.quantidade_devolvida_kg += quantidade
    venda.save(update_fields=("quantidade_devolvida_kg", "atualizado_em"))
    return devolucao

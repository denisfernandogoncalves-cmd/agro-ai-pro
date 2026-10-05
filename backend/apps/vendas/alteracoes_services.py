"""Correções comerciais atômicas, com estorno e trilha antes/depois."""
from django.db import transaction
from django.utils import timezone

from apps.graos.models import ReservaSaldoGraos, normalizar_placa
from apps.graos.services import (
    _bloquear_armazens, _bloquear_cadpros_para_saldo, estornar_movimentacao,
    liberar_reserva, reservar_saldo, confirmar_entrega, registrar_devolucao,
)
from .models import AlteracaoVendaGraos, DevolucaoVendaGraos, EntregaVendaGraos, VendaGraos, ZERO
from .services import (
    VendaGraosConflitoError, VendaGraosError, _chave, _hash, _lote_operacional,
    _quantidade, _validar_contexto_venda, _validar_repeticao, _validar_resultado_posicao,
    _resultado_ledger,
)


def _snapshot(venda):
    campos = ("numero_contrato", "cliente_nome", "contrato_id", "posicao_id", "lote_id",
              "quantidade_kg", "quantidade_entregue_kg", "quantidade_devolvida_kg",
              "quantidade_cancelada_kg", "status", "reserva_id", "data_contrato",
              "data_limite_entrega", "observacoes", "versao", "excluida_em")
    return {
        **{campo: getattr(venda, campo) for campo in campos},
        "entregas": list(venda.entregas.values("id", "quantidade_kg", "data_entrega", "destino", "placa", "motorista", "nota_produtor", "nota_empresa", "referencia_externa", "observacoes", "cancelado_em", "movimentacao_id")),
        "devolucoes": list(venda.devolucoes.values("id", "quantidade_kg", "data_devolucao", "referencia_externa", "observacoes", "cancelado_em", "movimentacao_id")),
    }


def _iniciar(*, venda, chave, tipo, versao, motivo, dados):
    chave = _chave(chave)
    motivo = str(motivo or "").strip()
    if not motivo:
        raise VendaGraosError("Informe o motivo da edição ou exclusão.")
    payload = {**dados, "venda": venda.pk, "tipo": tipo, "versao": versao, "motivo": motivo}
    assinatura = _hash(payload)
    venda = VendaGraos.objects.select_for_update().get(pk=venda.pk)
    anterior = AlteracaoVendaGraos.objects.filter(chave=chave).first()
    if anterior:
        _validar_repeticao(anterior.hash_requisicao, assinatura)
        return venda, None, assinatura
    if venda.excluida_em:
        raise VendaGraosConflitoError("A venda foi excluída e permanece apenas no histórico.")
    if venda.versao != versao:
        raise VendaGraosConflitoError("A venda mudou. Atualize a tela antes de editar ou excluir.")
    return venda, _snapshot(venda), assinatura


def _bloquear(venda, nova_posicao=None):
    posicoes = [venda.posicao] + ([nova_posicao] if nova_posicao else [])
    _bloquear_cadpros_para_saldo(p.cad_pro_id for p in posicoes)
    _bloquear_armazens(p.armazem_id for p in posicoes)
    _validar_contexto_venda(venda)


def _liberar(usuario, reserva_id, chave, motivo):
    if not reserva_id:
        return
    reserva = ReservaSaldoGraos.objects.get(pk=reserva_id)
    if reserva.saldo_reservado_kg > ZERO:
        liberar_reserva(usuario=usuario, reserva=reserva, chave_idempotencia=chave,
                        observacoes=motivo)


def _situacao(usuario, venda, status_original, chave, motivo):
    venda.reserva = None
    restante = venda.quantidade_kg - venda.quantidade_entregue_kg
    venda.quantidade_cancelada_kg = restante if status_original == "cancelada" else ZERO
    if status_original in ("rascunho", "cancelada"):
        venda.status = status_original
    else:
        venda.status = "entregue" if restante == ZERO else (
            "parcial" if venda.quantidade_entregue_kg else "confirmada"
        )
        if restante > ZERO:
            resultado = reservar_saldo(
                usuario=usuario, lote=venda.lote, quantidade_kg=restante,
                permitir_saldo_negativo=True,
                chave_idempotencia=chave, referencia_externa=venda.numero_contrato,
                observacoes=motivo, metadados={"venda_id": venda.pk},
            )
            _validar_resultado_posicao(venda, resultado)
            venda.reserva = ReservaSaldoGraos.objects.get(pk=resultado.reserva.id)


def _registrar(usuario, venda, tipo, chave, assinatura, motivo, antes):
    venda.versao += 1
    venda.full_clean()
    venda.save()
    AlteracaoVendaGraos.objects.create(
        venda=venda, tipo=tipo, chave=chave, hash_requisicao=assinatura,
        motivo=motivo, antes=antes, depois=_snapshot(venda), criado_por=usuario,
    )
    return venda


def _estornar(usuario, item, chave, motivo):
    estornar_movimentacao(
        usuario=usuario, movimentacao=item.movimentacao, chave_idempotencia=chave,
        observacoes=motivo, permitir_venda=True,
    )
    item.cancelado_em = timezone.now()
    item.save(update_fields=("cancelado_em",))
    if isinstance(item, EntregaVendaGraos):
        _liberar(usuario, item.movimentacao.reserva_id, f"{chave}:lib", motivo)


@transaction.atomic
def editar_venda(*, usuario, venda, chave_idempotencia, versao, motivo, **dados):
    venda, antes, assinatura = _iniciar(venda=venda, chave=chave_idempotencia,
        tipo="editar_venda", versao=versao, motivo=motivo, dados=dados)
    if antes is None:
        return venda
    token = _hash({"chave": chave_idempotencia})
    status_original = venda.status
    nova_posicao = dados.get("posicao", venda.posicao)
    quantidade = _quantidade(dados.get("quantidade_kg", venda.quantidade_kg))
    if quantidade < venda.quantidade_entregue_kg:
        raise VendaGraosConflitoError("Corrija as entregas antes de reduzir o contrato abaixo do peso já entregue.")
    if nova_posicao.pk != venda.posicao_id and venda.quantidade_entregue_kg > ZERO:
        raise VendaGraosConflitoError("Corrija ou exclua as entregas antes de trocar a posição de estoque.")
    mudou_saldo = nova_posicao.pk != venda.posicao_id or quantidade != venda.quantidade_kg
    if mudou_saldo:
        _bloquear(venda, nova_posicao)
        _liberar(usuario, venda.reserva_id, f"ve:{token}:lib", motivo)
        venda.posicao = nova_posicao
        venda.lote = _lote_operacional(nova_posicao)
    contrato = dados.get("contrato")
    if contrato:
        if not contrato.ativo and contrato.pk != venda.contrato_id:
            raise VendaGraosError("O contrato selecionado está inativo.")
        dados.update(numero_contrato=contrato.numero, cliente_nome=contrato.empresa)
    for campo in ("numero_contrato", "cliente_nome", "contrato", "data_contrato", "data_limite_entrega", "observacoes"):
        if campo in dados:
            setattr(venda, campo, dados[campo])
    venda.quantidade_kg = quantidade
    if venda.data_limite_entrega and venda.data_limite_entrega < venda.data_contrato:
        raise VendaGraosError("A data limite não pode anteceder o contrato.")
    if mudou_saldo:
        _situacao(usuario, venda, status_original, f"ve:{token}:res", motivo)
    return _registrar(usuario, venda, "editar_venda", chave_idempotencia, assinatura, motivo, antes)


@transaction.atomic
def excluir_venda(*, usuario, venda, chave_idempotencia, versao, motivo):
    venda, antes, assinatura = _iniciar(venda=venda, chave=chave_idempotencia,
        tipo="excluir_venda", versao=versao, motivo=motivo, dados={})
    if antes is None:
        return venda
    token = _hash({"chave": chave_idempotencia})
    tem_movimentos = venda.entregas.filter(cancelado_em__isnull=True).exists() or venda.devolucoes.filter(cancelado_em__isnull=True).exists()
    if venda.reserva_id or tem_movimentos:
        _bloquear(venda)
        _liberar(usuario, venda.reserva_id, f"vx:{token}:lib", motivo)
    for relacao in (venda.devolucoes, venda.entregas):
        for item in relacao.filter(cancelado_em__isnull=True).order_by("-id"):
            _estornar(usuario, item, f"vx:{token}:{item._meta.model_name}:{item.pk}", motivo)
    venda.quantidade_entregue_kg = ZERO
    venda.quantidade_devolvida_kg = ZERO
    venda.quantidade_cancelada_kg = venda.quantidade_kg
    venda.status = "cancelada"
    venda.excluida_em = timezone.now()
    return _registrar(usuario, venda, "excluir_venda", chave_idempotencia, assinatura, motivo, antes)


@transaction.atomic
def alterar_movimento(*, usuario, venda, movimento_id, natureza, excluir,
                      chave_idempotencia, versao, motivo, **dados):
    tipo = f"{'excluir' if excluir else 'editar'}_{natureza}"
    venda, antes, assinatura = _iniciar(venda=venda, chave=chave_idempotencia,
        tipo=tipo, versao=versao, motivo=motivo, dados={**dados, "movimento_id": movimento_id})
    if antes is None:
        return venda
    modelo = EntregaVendaGraos if natureza == "entrega" else DevolucaoVendaGraos
    item = modelo.objects.filter(pk=movimento_id, venda=venda, cancelado_em__isnull=True).first()
    if not item:
        raise VendaGraosConflitoError("O lançamento não pertence à venda ou já foi excluído/substituído.")
    quantidade_nova = ZERO if excluir else _quantidade(dados["quantidade_kg"])
    entregue = venda.quantidade_entregue_kg + (quantidade_nova - item.quantidade_kg if natureza == "entrega" else ZERO)
    devolvida = venda.quantidade_devolvida_kg + (quantidade_nova - item.quantidade_kg if natureza == "devolucao" else ZERO)
    if not ZERO <= devolvida <= entregue <= venda.quantidade_kg:
        raise VendaGraosConflitoError("A alteração conflita com o total contratado, entregue ou devolvido. Corrija primeiro os lançamentos dependentes.")
    token = _hash({"chave": chave_idempotencia})
    status_original = venda.status
    _bloquear(venda)
    _liberar(usuario, venda.reserva_id, f"vm:{token}:lib", motivo)
    _estornar(usuario, item, f"vm:{token}:est", motivo)
    if not excluir:
        campos = ("referencia_externa", "observacoes")
        if natureza == "entrega":
            campos += ("destino", "placa", "motorista", "nota_produtor", "nota_empresa", "peso_bruto_kg", "tara_kg", "umidade_percentual", "avariados_percentual", "quebrados_percentual", "ph")
        novos = {campo: dados.get(campo, getattr(item, campo)) for campo in campos}
        if natureza == "entrega" and novos.get("peso_bruto_kg") is not None and (novos.get("tara_kg") is None or novos["peso_bruto_kg"] - novos["tara_kg"] != quantidade_nova):
            raise VendaGraosError("Confira peso bruto e tara para a nova quantidade líquida.")
        campo_data = "data_entrega" if natureza == "entrega" else "data_devolucao"
        data = dados.get("data_movimento", getattr(item, campo_data))
        if natureza == "entrega":
            novos["placa"] = normalizar_placa(novos["placa"])
            if novos["placa"] and len(novos["placa"]) != 7:
                raise VendaGraosError("Informe uma placa brasileira com 7 letras e números.")
            reserva = reservar_saldo(usuario=usuario, lote=venda.lote,
                permitir_saldo_negativo=True,
                quantidade_kg=quantidade_nova, chave_idempotencia=f"vm:{token}:temp", metadados={"venda_id": venda.pk})
            _validar_resultado_posicao(venda, reserva)
            resultado = confirmar_entrega(usuario=usuario,
                permitir_saldo_negativo=True,
                reserva=ReservaSaldoGraos.objects.get(pk=reserva.reserva.id),
                quantidade_kg=quantidade_nova, data_movimento=data,
                chave_idempotencia=f"vm:{token}:novo", observacoes=motivo, metadados={"venda_id": venda.pk})
        else:
            resultado = registrar_devolucao(usuario=usuario, lote=venda.lote,
                quantidade_kg=quantidade_nova, data_movimento=data,
                chave_idempotencia=f"vm:{token}:novo", observacoes=motivo, metadados={"venda_id": venda.pk})
        _validar_resultado_posicao(venda, resultado)
        origem, movimento = _resultado_ledger(resultado)
        modelo.objects.create(venda=venda, quantidade_kg=quantidade_nova,
            **{campo_data: data}, **novos, origem=origem, movimentacao=movimento,
            chave_idempotencia=f"vm:{token}:novo",
            hash_requisicao=assinatura, criado_por=usuario)
    venda.quantidade_entregue_kg = entregue
    venda.quantidade_devolvida_kg = devolvida
    _situacao(usuario, venda, status_original, f"vm:{token}:res", motivo)
    return _registrar(usuario, venda, tipo, chave_idempotencia, assinatura, motivo, antes)

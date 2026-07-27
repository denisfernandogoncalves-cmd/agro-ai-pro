from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.core.access import PAPEIS_ADMINISTRACAO, PAPEIS_GESTAO, PAPEIS_OPERACAO

from .grain_models import MovimentacaoGraos
from .grain_services import ProducaoError, registrar_movimentacao
from .joint_access import exigir_acesso_lote
from .joint_calculations import (
    rateio_manual,
    rateio_por_area,
    recalcular_lote,
    validar_lote_para_confirmacao,
)
from .joint_inventory import (
    auditar,
    dados_auditaveis,
    distribuir_saldo_lote,
    registrar_movimento_conjunto,
    saldo_bloqueado,
)
from .joint_models import (
    LoteConjuntoProducao,
    MovimentacaoLoteConjunto,
    ParticipanteLoteConjunto,
)


@transaction.atomic
def confirmar_lote(lote, *, usuario):
    lote = LoteConjuntoProducao.objects.select_for_update().get(pk=lote.pk)
    exigir_acesso_lote(usuario, lote, papeis=PAPEIS_GESTAO)
    if lote.status not in {
        LoteConjuntoProducao.Status.RASCUNHO,
        LoteConjuntoProducao.Status.CONFERENCIA,
    }:
        raise ProducaoError("Somente lotes em rascunho ou conferência podem ser confirmados.")
    recalcular_lote(lote)
    participantes = validar_lote_para_confirmacao(lote)
    anteriores = dados_auditaveis(lote)
    registrar_movimento_conjunto(
        usuario=usuario,
        lote=lote,
        tipo=MovimentacaoLoteConjunto.Tipo.ENTRADA,
        quantidade=lote.peso_liquido_total_kg,
        local_destino=lote.local_armazenagem,
        referencia_tipo="confirmacao_lote",
        referencia_id=lote.pk,
    )
    lote.status = LoteConjuntoProducao.Status.CONFIRMADO
    lote.confirmado_por = usuario
    lote.confirmado_em = timezone.now()
    lote.save(update_fields=("status", "confirmado_por", "confirmado_em", "atualizado_em"))
    auditar(
        usuario=usuario,
        acao="lote_conjunto_confirmado",
        objeto=lote,
        anteriores=anteriores,
        metadados={
            "propriedades": [item.propriedade_id for item in participantes],
            "cargas": lote.cargas.count(),
            "modo_rateio": lote.modo_rateio,
        },
    )
    if lote.modo_rateio == LoteConjuntoProducao.ModoRateio.AREA:
        distribuir_saldo_lote(
            lote,
            usuario=usuario,
            distribuicoes=rateio_por_area(lote, participantes),
            metodo=ParticipanteLoteConjunto.MetodoRateio.AREA,
            justificativa="Rateio por área escolhido explicitamente pelo usuário.",
        )
    elif lote.modo_rateio == LoteConjuntoProducao.ModoRateio.MANUAL:
        justificativa = "; ".join(
            item.justificativa_rateio.strip()
            for item in participantes
            if item.justificativa_rateio.strip()
        )
        distribuir_saldo_lote(
            lote,
            usuario=usuario,
            distribuicoes=rateio_manual(lote, participantes),
            metodo=ParticipanteLoteConjunto.MetodoRateio.MANUAL,
            justificativa=justificativa,
        )
    return lote


@transaction.atomic
def colocar_em_conferencia(lote, *, usuario):
    lote = LoteConjuntoProducao.objects.select_for_update().get(pk=lote.pk)
    exigir_acesso_lote(usuario, lote, papeis=PAPEIS_GESTAO)
    if lote.status != LoteConjuntoProducao.Status.RASCUNHO:
        raise ProducaoError("Somente lotes em rascunho podem entrar em conferência.")
    recalcular_lote(lote)
    validar_lote_para_confirmacao(lote)
    anteriores = dados_auditaveis(lote)
    lote.status = LoteConjuntoProducao.Status.CONFERENCIA
    lote.save(update_fields=("status", "atualizado_em"))
    auditar(
        usuario=usuario,
        acao="lote_conjunto_em_conferencia",
        objeto=lote,
        anteriores=anteriores,
    )
    return lote


@transaction.atomic
def transferir_saldo_conjunto(lote, *, usuario, origem, destino, quantidade_kg, motivo):
    lote = LoteConjuntoProducao.objects.select_for_update().get(pk=lote.pk)
    exigir_acesso_lote(usuario, lote, papeis=PAPEIS_OPERACAO)
    if origem.pk == destino.pk:
        raise ProducaoError("Origem e destino devem ser diferentes.")
    if not motivo.strip():
        raise ProducaoError("Informe o motivo da transferência.")
    return registrar_movimento_conjunto(
        usuario=usuario,
        lote=lote,
        tipo=MovimentacaoLoteConjunto.Tipo.TRANSFERENCIA,
        quantidade=quantidade_kg,
        local_origem=origem,
        local_destino=destino,
        motivo=motivo,
    )


@transaction.atomic
def ajustar_saldo_conjunto(lote, *, usuario, local, quantidade_kg, entrada, justificativa):
    lote = LoteConjuntoProducao.objects.select_for_update().get(pk=lote.pk)
    exigir_acesso_lote(usuario, lote, papeis=PAPEIS_ADMINISTRACAO)
    if not justificativa.strip():
        raise ProducaoError("Ajustes administrativos exigem justificativa.")
    return registrar_movimento_conjunto(
        usuario=usuario,
        lote=lote,
        tipo=(
            MovimentacaoLoteConjunto.Tipo.AJUSTE_ENTRADA
            if entrada
            else MovimentacaoLoteConjunto.Tipo.AJUSTE_SAIDA
        ),
        quantidade=quantidade_kg,
        local_destino=local if entrada else None,
        local_origem=None if entrada else local,
        motivo=justificativa,
    )


@transaction.atomic
def encerrar_lote(lote, *, usuario):
    lote = LoteConjuntoProducao.objects.select_for_update().get(pk=lote.pk)
    exigir_acesso_lote(usuario, lote, papeis=PAPEIS_GESTAO)
    if lote.status != LoteConjuntoProducao.Status.CONFIRMADO:
        raise ProducaoError("Somente lotes confirmados podem ser encerrados.")
    anteriores = dados_auditaveis(lote)
    lote.status = LoteConjuntoProducao.Status.ENCERRADO
    lote.encerrado_em = timezone.now()
    lote.save(update_fields=("status", "encerrado_em", "atualizado_em"))
    auditar(usuario=usuario, acao="lote_conjunto_encerrado", objeto=lote, anteriores=anteriores)
    return lote


@transaction.atomic
def estornar_lote(lote, *, usuario, motivo):
    lote = LoteConjuntoProducao.objects.select_for_update().get(pk=lote.pk)
    exigir_acesso_lote(usuario, lote, papeis=PAPEIS_ADMINISTRACAO)
    if lote.status not in {
        LoteConjuntoProducao.Status.CONFIRMADO,
        LoteConjuntoProducao.Status.ENCERRADO,
    }:
        raise ProducaoError("Somente lotes confirmados ou encerrados podem ser estornados.")
    if not motivo.strip():
        raise ProducaoError("O estorno exige justificativa.")
    if lote.saidas_conjuntas.filter(status="confirmada").exists():
        raise ProducaoError("Estorne primeiro todas as saídas confirmadas deste lote.")
    distribuicoes = list(lote.cadpros_participantes.select_related("cadpro__propriedade", "participante"))
    for vinculo in distribuicoes:
        if vinculo.quantidade_atribuida_kg <= 0:
            continue
        participante = vinculo.participante
        vinculos_talhao = list(participante.talhoes.select_related("talhao")) if participante else []
        talhao = vinculos_talhao[0].talhao if len(vinculos_talhao) == 1 else None
        registrar_movimentacao(
            usuario=usuario,
            tipo=MovimentacaoGraos.Tipo.SAIDA,
            propriedade=vinculo.cadpro.propriedade,
            cadpro=vinculo.cadpro,
            talhao=talhao,
            cultura=lote.cultura,
            safra=lote.safra,
            quantidade_kg=vinculo.quantidade_atribuida_kg,
            local_origem=lote.local_armazenagem,
            referencia_tipo="estorno_lote_conjunto",
            referencia_id=lote.pk,
            motivo=motivo,
        )
        registrar_movimento_conjunto(
            usuario=usuario,
            lote=lote,
            tipo=MovimentacaoLoteConjunto.Tipo.ESTORNO,
            quantidade=vinculo.quantidade_atribuida_kg,
            local_destino=lote.local_armazenagem,
            participante=participante,
            cadpro=vinculo.cadpro,
            motivo=motivo,
            referencia_tipo="estorno_distribuicao",
            referencia_id=vinculo.pk,
        )
        vinculo.quantidade_atribuida_kg = Decimal("0")
        vinculo.save(update_fields=("quantidade_atribuida_kg", "atualizado_em"))
    saldo = saldo_bloqueado(lote, lote.local_armazenagem)
    if saldo.quantidade_kg > 0:
        registrar_movimento_conjunto(
            usuario=usuario,
            lote=lote,
            tipo=MovimentacaoLoteConjunto.Tipo.ESTORNO,
            quantidade=saldo.quantidade_kg,
            local_origem=lote.local_armazenagem,
            motivo=motivo,
            referencia_tipo="estorno_lote_conjunto",
            referencia_id=lote.pk,
        )
    anteriores = dados_auditaveis(lote)
    lote.status = LoteConjuntoProducao.Status.ESTORNADO
    lote.estornado_em = timezone.now()
    lote.save(update_fields=("status", "estornado_em", "atualizado_em"))
    auditar(
        usuario=usuario,
        acao="lote_conjunto_estornado",
        objeto=lote,
        anteriores=anteriores,
        metadados={"motivo": motivo},
    )
    return lote

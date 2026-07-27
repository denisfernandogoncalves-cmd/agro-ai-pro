from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Exists, OuterRef, Sum
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied

from apps.core.access import (
    PAPEIS_ADMINISTRACAO,
    PAPEIS_GESTAO,
    PAPEIS_LEITURA,
    PAPEIS_OPERACAO,
    exigir_acesso_propriedade,
    ids_propriedades_usuario,
)

from .grain_access import exigir_acesso_cadpro
from .grain_models import CadPro, MovimentacaoGraos
from .grain_services import ProducaoError, registrar_auditoria, registrar_movimentacao
from .joint_models import (
    CadProLoteConjunto,
    CargaLoteConjunto,
    LoteConjuntoProducao,
    MovimentacaoLoteConjunto,
    ParticipanteLoteConjunto,
    SaidaLoteConjunto,
    SaldoLoteConjunto,
)


KG = Decimal("0.001")
AREA = Decimal("0.0001")
PERCENTUAL = Decimal("0.00001")


def quantizar_kg(valor):
    return Decimal(str(valor)).quantize(KG, rounding=ROUND_HALF_UP)


def converter_para_kg(valor, unidade, cultura):
    quantidade = Decimal(str(valor))
    if unidade == "kg":
        return quantizar_kg(quantidade)
    if unidade == "toneladas":
        return quantizar_kg(quantidade * Decimal("1000"))
    if unidade == "sacas":
        return quantizar_kg(quantidade * cultura.peso_saca_kg)
    raise ProducaoError("Unidade inválida. Use kg, toneladas ou sacas.")


def lotes_conjuntos_visiveis(usuario):
    queryset = LoteConjuntoProducao.objects.all()
    ids = ids_propriedades_usuario(usuario)
    if ids is None:
        return queryset
    if not ids:
        return queryset.none()
    participantes_nao_autorizados = ParticipanteLoteConjunto.objects.filter(
        lote_id=OuterRef("pk")
    ).exclude(propriedade_id__in=ids)
    return queryset.annotate(
        possui_participante_nao_autorizado=Exists(participantes_nao_autorizados)
    ).filter(possui_participante_nao_autorizado=False, participantes__isnull=False).distinct()


def exigir_acesso_lote(usuario, lote, *, papeis=PAPEIS_LEITURA, ocultar=False):
    participantes = list(lote.participantes.select_related("propriedade", "cadpro"))
    if not participantes:
        if usuario and usuario.is_superuser:
            return
        raise PermissionDenied("O lote precisa possuir propriedades participantes autorizadas.")
    for participante in participantes:
        exigir_acesso_propriedade(
            usuario,
            participante.propriedade,
            papeis=papeis,
            ocultar=ocultar,
        )
        if participante.cadpro_id:
            exigir_acesso_cadpro(
                usuario,
                participante.cadpro,
                papeis=papeis,
                ocultar=ocultar,
            )


def validar_acesso_propriedades(usuario, propriedades, *, papeis=PAPEIS_GESTAO):
    propriedades = list(propriedades)
    if len({item.pk for item in propriedades}) < 2:
        raise ProducaoError("O lote conjunto deve reunir pelo menos duas propriedades distintas.")
    for propriedade in propriedades:
        exigir_acesso_propriedade(usuario, propriedade, papeis=papeis)


def _media_ponderada(cargas, campo, total_liquido):
    if not total_liquido:
        return Decimal("0")
    soma = sum((Decimal(str(getattr(carga, campo))) * carga.peso_liquido_kg for carga in cargas), Decimal("0"))
    return (soma / total_liquido).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


@transaction.atomic
def recalcular_lote(lote):
    lote = LoteConjuntoProducao.objects.select_for_update().get(pk=lote.pk)
    participantes = list(lote.participantes.select_for_update())
    cargas = list(lote.cargas.select_for_update())

    area_cadastrada = sum((item.area_cadastrada_ha for item in participantes), Decimal("0"))
    area_colhida = sum((item.area_colhida_ha for item in participantes), Decimal("0"))
    bruto = sum((item.peso_bruto_kg for item in cargas), Decimal("0"))
    tara = sum((item.tara_kg for item in cargas), Decimal("0"))
    liquido = sum((item.peso_liquido_kg for item in cargas), Decimal("0"))

    for participante in participantes:
        percentual = Decimal("0")
        if area_colhida:
            percentual = (participante.area_colhida_ha / area_colhida * Decimal("100")).quantize(
                PERCENTUAL,
                rounding=ROUND_HALF_UP,
            )
        participante.percentual_area = percentual
        participante.save(update_fields=("percentual_area", "atualizado_em"))

    lote.area_total_cadastrada_ha = area_cadastrada.quantize(AREA)
    lote.area_total_colhida_ha = area_colhida.quantize(AREA)
    lote.peso_bruto_total_kg = quantizar_kg(bruto)
    lote.tara_total_kg = quantizar_kg(tara)
    lote.peso_liquido_total_kg = quantizar_kg(liquido)
    lote.umidade_media = _media_ponderada(cargas, "umidade_percentual", liquido)
    lote.impureza_media = _media_ponderada(cargas, "impureza_percentual", liquido)
    lote.defeitos_medios = _media_ponderada(cargas, "defeitos_percentual", liquido)
    lote.save(
        update_fields=(
            "area_total_cadastrada_ha",
            "area_total_colhida_ha",
            "peso_bruto_total_kg",
            "tara_total_kg",
            "peso_liquido_total_kg",
            "umidade_media",
            "impureza_media",
            "defeitos_medios",
            "atualizado_em",
        )
    )
    return lote


def _saldo_bloqueado(lote, local):
    saldo, _ = SaldoLoteConjunto.objects.select_for_update().get_or_create(
        lote=lote,
        local_armazenagem=local,
        defaults={"quantidade_kg": Decimal("0")},
    )
    return saldo


def _creditar_saldo(lote, local, quantidade):
    saldo = _saldo_bloqueado(lote, local)
    anterior = saldo.quantidade_kg
    saldo.quantidade_kg = quantizar_kg(anterior + quantidade)
    saldo.full_clean()
    saldo.save(update_fields=("quantidade_kg", "atualizado_em"))
    return saldo, anterior


def _debitar_saldo(lote, local, quantidade):
    saldo = _saldo_bloqueado(lote, local)
    anterior = saldo.quantidade_kg
    posterior = quantizar_kg(anterior - quantidade)
    if posterior < 0:
        raise ProducaoError(
            f"Saldo conjunto insuficiente. Disponível: {anterior} kg; solicitado: {quantidade} kg."
        )
    saldo.quantidade_kg = posterior
    saldo.full_clean()
    saldo.save(update_fields=("quantidade_kg", "atualizado_em"))
    return saldo, anterior


def saldo_conjunto_total(lote):
    return lote.saldos_conjuntos.aggregate(total=Sum("quantidade_kg"))["total"] or Decimal("0")


def _criar_movimentacao(
    *,
    lote,
    usuario,
    tipo,
    quantidade,
    local_origem=None,
    local_destino=None,
    participante=None,
    cadpro=None,
    referencia_tipo="",
    referencia_id=None,
    motivo="",
    estorno_de=None,
):
    quantidade = quantizar_kg(quantidade)
    origem_anterior = origem_posterior = destino_anterior = destino_posterior = None

    if tipo in {
        MovimentacaoLoteConjunto.Tipo.SAIDA,
        MovimentacaoLoteConjunto.Tipo.DISTRIBUICAO,
        MovimentacaoLoteConjunto.Tipo.AJUSTE_SAIDA,
    }:
        saldo, origem_anterior = _debitar_saldo(lote, local_origem, quantidade)
        origem_posterior = saldo.quantidade_kg
    elif tipo in {
        MovimentacaoLoteConjunto.Tipo.ENTRADA,
        MovimentacaoLoteConjunto.Tipo.AJUSTE_ENTRADA,
    }:
        saldo, destino_anterior = _creditar_saldo(lote, local_destino, quantidade)
        destino_posterior = saldo.quantidade_kg
    elif tipo == MovimentacaoLoteConjunto.Tipo.TRANSFERENCIA:
        saldo_origem, origem_anterior = _debitar_saldo(lote, local_origem, quantidade)
        saldo_destino, destino_anterior = _creditar_saldo(lote, local_destino, quantidade)
        origem_posterior = saldo_origem.quantidade_kg
        destino_posterior = saldo_destino.quantidade_kg
    elif tipo == MovimentacaoLoteConjunto.Tipo.ESTORNO:
        if not estorno_de:
            raise ProducaoError("Informe a movimentação a estornar.")
        if MovimentacaoLoteConjunto.objects.filter(estorno_de=estorno_de).exists():
            raise ProducaoError("Esta movimentação já foi estornada.")
        if estorno_de.tipo in {
            MovimentacaoLoteConjunto.Tipo.SAIDA,
            MovimentacaoLoteConjunto.Tipo.DISTRIBUICAO,
            MovimentacaoLoteConjunto.Tipo.AJUSTE_SAIDA,
        }:
            saldo, destino_anterior = _creditar_saldo(lote, estorno_de.local_origem, quantidade)
            local_destino = estorno_de.local_origem
            destino_posterior = saldo.quantidade_kg
        elif estorno_de.tipo in {
            MovimentacaoLoteConjunto.Tipo.ENTRADA,
            MovimentacaoLoteConjunto.Tipo.AJUSTE_ENTRADA,
        }:
            saldo, origem_anterior = _debitar_saldo(lote, estorno_de.local_destino, quantidade)
            local_origem = estorno_de.local_destino
            origem_posterior = saldo.quantidade_kg
        elif estorno_de.tipo == MovimentacaoLoteConjunto.Tipo.TRANSFERENCIA:
            saldo_destino, origem_anterior = _debitar_saldo(lote, estorno_de.local_destino, quantidade)
            saldo_origem, destino_anterior = _creditar_saldo(lote, estorno_de.local_origem, quantidade)
            local_origem = estorno_de.local_destino
            local_destino = estorno_de.local_origem
            origem_posterior = saldo_destino.quantidade_kg
            destino_posterior = saldo_origem.quantidade_kg
        else:
            raise ProducaoError("Movimentações de estorno não podem ser estornadas novamente.")

    movimento = MovimentacaoLoteConjunto.objects.create(
        lote=lote,
        tipo=tipo,
        local_origem=local_origem,
        local_destino=local_destino,
        participante=participante,
        cadpro=cadpro,
        quantidade_kg=quantidade,
        saldo_origem_anterior=origem_anterior,
        saldo_origem_posterior=origem_posterior,
        saldo_destino_anterior=destino_anterior,
        saldo_destino_posterior=destino_posterior,
        referencia_tipo=referencia_tipo,
        referencia_id=referencia_id,
        motivo=motivo,
        estorno_de=estorno_de,
        criado_por=usuario,
    )
    registrar_auditoria(
        usuario=usuario,
        acao="movimentacao_lote_conjunto",
        objeto=lote,
        metadados={
            "movimentacao": movimento.pk,
            "tipo": tipo,
            "quantidade_kg": str(quantidade),
            "saldo_origem_anterior": str(origem_anterior) if origem_anterior is not None else None,
            "saldo_origem_posterior": str(origem_posterior) if origem_posterior is not None else None,
            "saldo_destino_anterior": str(destino_anterior) if destino_anterior is not None else None,
            "saldo_destino_posterior": str(destino_posterior) if destino_posterior is not None else None,
            "motivo": motivo,
        },
    )
    return movimento


def _validar_confirmacao(lote, usuario):
    participantes = list(lote.participantes.select_related("propriedade", "cadpro"))
    validar_acesso_propriedades(
        usuario,
        [item.propriedade for item in participantes],
        papeis=PAPEIS_GESTAO,
    )
    if lote.status not in {LoteConjuntoProducao.Status.RASCUNHO, LoteConjuntoProducao.Status.CONFERENCIA}:
        raise ProducaoError("Somente lotes em rascunho ou conferência podem ser confirmados.")
    if not lote.cargas.exists():
        raise ProducaoError("Inclua ao menos uma carga antes de confirmar o lote.")
    if lote.area_total_colhida_ha <= 0:
        raise ProducaoError("A área efetivamente colhida deve ser maior que zero.")
    if lote.peso_liquido_total_kg <= 0:
        raise ProducaoError("O peso líquido total deve ser maior que zero.")
    if lote.local_armazenagem.propriedade_id and lote.local_armazenagem.propriedade_id not in {
        item.propriedade_id for item in participantes
    }:
        raise ProducaoError("O local de armazenagem deve ser compartilhado ou pertencer a uma propriedade participante.")
    for participante in participantes:
        participante.full_clean()
    return participantes


@transaction.atomic
def colocar_em_conferencia(lote, *, usuario):
    lote = LoteConjuntoProducao.objects.select_for_update().get(pk=lote.pk)
    exigir_acesso_lote(usuario, lote, papeis=PAPEIS_GESTAO)
    if lote.status != LoteConjuntoProducao.Status.RASCUNHO:
        raise ProducaoError("Somente lotes em rascunho podem entrar em conferência.")
    recalcular_lote(lote)
    lote.status = LoteConjuntoProducao.Status.CONFERENCIA
    lote.save(update_fields=("status", "atualizado_em"))
    registrar_auditoria(usuario=usuario, acao="lote_conjunto_em_conferencia", objeto=lote)
    return lote


@transaction.atomic
def confirmar_lote(lote, *, usuario):
    lote = LoteConjuntoProducao.objects.select_for_update().select_related(
        "cultura", "safra", "local_armazenagem"
    ).get(pk=lote.pk)
    lote = recalcular_lote(lote)
    participantes = _validar_confirmacao(lote, usuario)
    movimento = _criar_movimentacao(
        lote=lote,
        usuario=usuario,
        tipo=MovimentacaoLoteConjunto.Tipo.ENTRADA,
        quantidade=lote.peso_liquido_total_kg,
        local_destino=lote.local_armazenagem,
        referencia_tipo="lote_conjunto",
        referencia_id=lote.pk,
    )
    lote.status = LoteConjuntoProducao.Status.CONFIRMADO
    lote.confirmado_por = usuario
    lote.confirmado_em = timezone.now()
    lote.save(update_fields=("status", "confirmado_por", "confirmado_em", "atualizado_em"))
    registrar_auditoria(
        usuario=usuario,
        acao="lote_conjunto_confirmado",
        objeto=lote,
        metadados={
            "movimentacao_entrada": movimento.pk,
            "propriedades": [item.propriedade_id for item in participantes],
            "area_colhida_ha": str(lote.area_total_colhida_ha),
            "peso_liquido_kg": str(lote.peso_liquido_total_kg),
            "modo_rateio": lote.modo_rateio,
        },
    )
    if lote.modo_rateio == LoteConjuntoProducao.ModoRateio.AREA:
        _ratear_por_area_bloqueado(lote, usuario=usuario)
    elif lote.modo_rateio == LoteConjuntoProducao.ModoRateio.MANUAL:
        distribuicoes = [
            {
                "participante": item,
                "cadpro": item.cadpro,
                "quantidade_kg": item.quantidade_rateada_kg,
                "metodo": ParticipanteLoteConjunto.MetodoRateio.MANUAL,
                "justificativa": item.justificativa_rateio,
            }
            for item in participantes
            if item.quantidade_rateada_kg is not None
        ]
        _aplicar_distribuicoes(lote, distribuicoes, usuario=usuario, exigir_total=True)
    return lote


def _rateio_area(participantes, total):
    area_total = sum((item.area_colhida_ha for item in participantes), Decimal("0"))
    if area_total <= 0:
        raise ProducaoError("Não é possível ratear sem área colhida válida.")
    restante = quantizar_kg(total)
    resultado = []
    for indice, participante in enumerate(participantes):
        if indice == len(participantes) - 1:
            quantidade = restante
        else:
            quantidade = quantizar_kg(total * participante.area_colhida_ha / area_total)
            restante = quantizar_kg(restante - quantidade)
        resultado.append((participante, quantidade))
    return resultado


def _talhao_unico(participante):
    talhoes = list(participante.talhoes.select_related("talhao")[:2])
    return talhoes[0].talhao if len(talhoes) == 1 else None


def _aplicar_distribuicoes(lote, distribuicoes, *, usuario, exigir_total):
    lote = LoteConjuntoProducao.objects.select_for_update().select_related(
        "cultura", "safra", "local_armazenagem"
    ).get(pk=lote.pk)
    exigir_acesso_lote(usuario, lote, papeis=PAPEIS_GESTAO)
    if lote.status not in {LoteConjuntoProducao.Status.CONFIRMADO, LoteConjuntoProducao.Status.ENCERRADO}:
        raise ProducaoError("O lote deve estar confirmado para ser distribuído.")
    disponivel = saldo_conjunto_total(lote)
    normalizadas = []
    total = Decimal("0")
    for item in distribuicoes:
        participante = item["participante"]
        cadpro = item["cadpro"]
        quantidade = quantizar_kg(item["quantidade_kg"] or 0)
        if quantidade <= 0:
            raise ProducaoError("Todas as distribuições devem possuir quantidade positiva.")
        if participante.lote_id != lote.pk:
            raise ProducaoError("Participante inválido para este lote.")
        if not cadpro or cadpro.propriedade_id != participante.propriedade_id:
            raise ProducaoError("O CAD/PRO deve pertencer à propriedade participante.")
        exigir_acesso_cadpro(usuario, cadpro, papeis=PAPEIS_GESTAO)
        normalizadas.append({**item, "quantidade_kg": quantidade})
        total += quantidade
    total = quantizar_kg(total)
    if exigir_total and total != quantizar_kg(disponivel):
        raise ProducaoError(
            f"A soma do rateio ({total} kg) deve ser igual ao saldo conjunto disponível ({disponivel} kg)."
        )
    if total > disponivel:
        raise ProducaoError("A distribuição supera o saldo conjunto disponível.")

    movimentos = []
    for item in normalizadas:
        participante = item["participante"]
        cadpro = item["cadpro"]
        quantidade = item["quantidade_kg"]
        movimento_conjunto = _criar_movimentacao(
            lote=lote,
            usuario=usuario,
            tipo=MovimentacaoLoteConjunto.Tipo.DISTRIBUICAO,
            quantidade=quantidade,
            local_origem=lote.local_armazenagem,
            participante=participante,
            cadpro=cadpro,
            referencia_tipo="distribuicao_cadpro",
            referencia_id=participante.pk,
            motivo=item.get("justificativa", ""),
        )
        movimento_individual = registrar_movimentacao(
            usuario=usuario,
            tipo=MovimentacaoGraos.Tipo.ENTRADA,
            propriedade=participante.propriedade,
            cadpro=cadpro,
            talhao=_talhao_unico(participante),
            cultura=lote.cultura,
            safra=lote.safra,
            quantidade_kg=quantidade,
            local_destino=lote.local_armazenagem,
            referencia_tipo="lote_conjunto",
            referencia_id=lote.pk,
            motivo=f"Distribuição do lote conjunto {lote.codigo}",
        )
        vinculo, _ = CadProLoteConjunto.objects.get_or_create(
            lote=lote,
            cadpro=cadpro,
            defaults={
                "participante": participante,
                "criado_por": usuario,
                "metodo_rateio": item["metodo"],
            },
        )
        vinculo.participante = participante
        vinculo.quantidade_atribuida_kg = quantizar_kg(vinculo.quantidade_atribuida_kg + quantidade)
        vinculo.metodo_rateio = item["metodo"]
        vinculo.justificativa = item.get("justificativa", "")
        vinculo.full_clean()
        vinculo.save()
        participante.quantidade_rateada_kg = quantizar_kg(
            (participante.quantidade_rateada_kg or Decimal("0")) + quantidade
        )
        participante.metodo_rateio = item["metodo"]
        participante.justificativa_rateio = item.get("justificativa", "")
        participante.save(
            update_fields=(
                "quantidade_rateada_kg",
                "metodo_rateio",
                "justificativa_rateio",
                "atualizado_em",
            )
        )
        movimentos.append((movimento_conjunto.pk, movimento_individual.pk))
    registrar_auditoria(
        usuario=usuario,
        acao="lote_conjunto_distribuido",
        objeto=lote,
        metadados={
            "total_distribuido_kg": str(total),
            "movimentos": movimentos,
            "saldo_conjunto_posterior": str(saldo_conjunto_total(lote)),
        },
    )
    return movimentos


def _ratear_por_area_bloqueado(lote, *, usuario):
    participantes = list(lote.participantes.select_for_update().select_related("cadpro", "propriedade"))
    if any(not item.cadpro_id for item in participantes):
        raise ProducaoError("O rateio por área exige um CAD/PRO confiável para cada propriedade.")
    total = saldo_conjunto_total(lote)
    distribuicoes = [
        {
            "participante": participante,
            "cadpro": participante.cadpro,
            "quantidade_kg": quantidade,
            "metodo": ParticipanteLoteConjunto.MetodoRateio.AREA,
            "justificativa": "Rateio automático proporcional à área efetivamente colhida.",
        }
        for participante, quantidade in _rateio_area(participantes, total)
    ]
    return _aplicar_distribuicoes(lote, distribuicoes, usuario=usuario, exigir_total=True)


@transaction.atomic
def ratear_por_area(lote, *, usuario):
    lote = LoteConjuntoProducao.objects.select_for_update().get(pk=lote.pk)
    return _ratear_por_area_bloqueado(lote, usuario=usuario)


@transaction.atomic
def ratear_manual(lote, *, usuario, itens, justificativa, exigir_total=True):
    if not justificativa or not justificativa.strip():
        raise ProducaoError("O rateio manual exige justificativa.")
    participantes = {item.pk: item for item in lote.participantes.select_related("propriedade")}
    distribuicoes = []
    for item in itens:
        participante = participantes.get(int(item.get("participante", 0)))
        cadpro = CadPro.objects.select_related("propriedade").filter(pk=item.get("cadpro")).first()
        if not participante:
            raise ProducaoError("Participante inválido no rateio manual.")
        quantidade = converter_para_kg(item.get("quantidade", 0), item.get("unidade", "kg"), lote.cultura)
        distribuicoes.append(
            {
                "participante": participante,
                "cadpro": cadpro,
                "quantidade_kg": quantidade,
                "metodo": ParticipanteLoteConjunto.MetodoRateio.MANUAL,
                "justificativa": justificativa.strip(),
            }
        )
    return _aplicar_distribuicoes(lote, distribuicoes, usuario=usuario, exigir_total=exigir_total)


@transaction.atomic
def transferir_saldo_conjunto(lote, *, usuario, local_origem, local_destino, quantidade_kg):
    exigir_acesso_lote(usuario, lote, papeis=PAPEIS_OPERACAO)
    if local_origem.pk == local_destino.pk:
        raise ProducaoError("Origem e destino devem ser diferentes.")
    movimento = _criar_movimentacao(
        lote=lote,
        usuario=usuario,
        tipo=MovimentacaoLoteConjunto.Tipo.TRANSFERENCIA,
        quantidade=quantidade_kg,
        local_origem=local_origem,
        local_destino=local_destino,
        referencia_tipo="transferencia_lote_conjunto",
        referencia_id=lote.pk,
    )
    return movimento


@transaction.atomic
def ajustar_saldo_conjunto(lote, *, usuario, local, quantidade_kg, justificativa):
    exigir_acesso_lote(usuario, lote, papeis=PAPEIS_ADMINISTRACAO)
    if not justificativa or not justificativa.strip():
        raise ProducaoError("Ajustes administrativos exigem justificativa.")
    quantidade = quantizar_kg(quantidade_kg)
    if quantidade == 0:
        raise ProducaoError("A quantidade do ajuste não pode ser zero.")
    tipo = (
        MovimentacaoLoteConjunto.Tipo.AJUSTE_ENTRADA
        if quantidade > 0
        else MovimentacaoLoteConjunto.Tipo.AJUSTE_SAIDA
    )
    return _criar_movimentacao(
        lote=lote,
        usuario=usuario,
        tipo=tipo,
        quantidade=abs(quantidade),
        local_destino=local if quantidade > 0 else None,
        local_origem=local if quantidade < 0 else None,
        referencia_tipo="ajuste_lote_conjunto",
        referencia_id=lote.pk,
        motivo=justificativa.strip(),
    )


@transaction.atomic
def confirmar_saida_conjunta(saida, *, usuario):
    saida = SaidaLoteConjunto.objects.select_for_update().select_related(
        "lote", "local_armazenagem", "contrato", "comprador"
    ).get(pk=saida.pk)
    exigir_acesso_lote(usuario, saida.lote, papeis=PAPEIS_OPERACAO)
    if saida.status != SaidaLoteConjunto.Status.RASCUNHO:
        raise ProducaoError("Somente saídas em rascunho podem ser confirmadas.")
    saida.full_clean()
    movimento = _criar_movimentacao(
        lote=saida.lote,
        usuario=usuario,
        tipo=MovimentacaoLoteConjunto.Tipo.SAIDA,
        quantidade=saida.quantidade_kg,
        local_origem=saida.local_armazenagem,
        referencia_tipo="saida_lote_conjunto",
        referencia_id=saida.pk,
        motivo=saida.justificativa,
    )
    saida.movimentacao = movimento
    saida.status = SaidaLoteConjunto.Status.CONFIRMADA
    saida.save(update_fields=("movimentacao", "status", "atualizado_em"))
    registrar_auditoria(
        usuario=usuario,
        acao="saida_lote_conjunto_confirmada",
        objeto=saida.lote,
        metadados={"saida": saida.pk, "movimentacao": movimento.pk, "quantidade_kg": str(saida.quantidade_kg)},
    )
    return saida


@transaction.atomic
def estornar_saida_conjunta(saida, *, usuario, motivo):
    saida = SaidaLoteConjunto.objects.select_for_update().select_related("lote", "movimentacao").get(pk=saida.pk)
    exigir_acesso_lote(usuario, saida.lote, papeis=PAPEIS_ADMINISTRACAO)
    if saida.status != SaidaLoteConjunto.Status.CONFIRMADA or not saida.movimentacao_id:
        raise ProducaoError("Somente saídas confirmadas podem ser estornadas.")
    if not motivo or not motivo.strip():
        raise ProducaoError("O estorno exige justificativa.")
    movimento = _criar_movimentacao(
        lote=saida.lote,
        usuario=usuario,
        tipo=MovimentacaoLoteConjunto.Tipo.ESTORNO,
        quantidade=saida.quantidade_kg,
        motivo=motivo.strip(),
        estorno_de=saida.movimentacao,
        referencia_tipo="saida_lote_conjunto",
        referencia_id=saida.pk,
    )
    saida.status = SaidaLoteConjunto.Status.ESTORNADA
    saida.save(update_fields=("status", "atualizado_em"))
    registrar_auditoria(
        usuario=usuario,
        acao="saida_lote_conjunto_estornada",
        objeto=saida.lote,
        metadados={"saida": saida.pk, "movimentacao_estorno": movimento.pk, "motivo": motivo.strip()},
    )
    return saida


@transaction.atomic
def encerrar_lote(lote, *, usuario):
    lote = LoteConjuntoProducao.objects.select_for_update().get(pk=lote.pk)
    exigir_acesso_lote(usuario, lote, papeis=PAPEIS_GESTAO)
    if lote.status != LoteConjuntoProducao.Status.CONFIRMADO:
        raise ProducaoError("Somente lotes confirmados podem ser encerrados.")
    if saldo_conjunto_total(lote) > 0:
        raise ProducaoError("O lote ainda possui saldo conjunto disponível.")
    lote.status = LoteConjuntoProducao.Status.ENCERRADO
    lote.encerrado_em = timezone.now()
    lote.save(update_fields=("status", "encerrado_em", "atualizado_em"))
    registrar_auditoria(usuario=usuario, acao="lote_conjunto_encerrado", objeto=lote)
    return lote


@transaction.atomic
def estornar_lote(lote, *, usuario, motivo):
    lote = LoteConjuntoProducao.objects.select_for_update().get(pk=lote.pk)
    exigir_acesso_lote(usuario, lote, papeis=PAPEIS_ADMINISTRACAO)
    if lote.status != LoteConjuntoProducao.Status.CONFIRMADO:
        raise ProducaoError("Somente lotes confirmados podem ser estornados.")
    if not motivo or not motivo.strip():
        raise ProducaoError("O estorno exige justificativa.")
    movimentos_posteriores = lote.movimentacoes_conjuntas.exclude(tipo=MovimentacaoLoteConjunto.Tipo.ENTRADA)
    if movimentos_posteriores.exists():
        raise ProducaoError("Estorne primeiro saídas, transferências ou distribuições vinculadas ao lote.")
    entrada = lote.movimentacoes_conjuntas.filter(tipo=MovimentacaoLoteConjunto.Tipo.ENTRADA).first()
    if not entrada:
        raise ProducaoError("A entrada original do lote não foi localizada.")
    movimento = _criar_movimentacao(
        lote=lote,
        usuario=usuario,
        tipo=MovimentacaoLoteConjunto.Tipo.ESTORNO,
        quantidade=entrada.quantidade_kg,
        estorno_de=entrada,
        motivo=motivo.strip(),
        referencia_tipo="lote_conjunto",
        referencia_id=lote.pk,
    )
    lote.status = LoteConjuntoProducao.Status.ESTORNADO
    lote.estornado_em = timezone.now()
    lote.save(update_fields=("status", "estornado_em", "atualizado_em"))
    registrar_auditoria(
        usuario=usuario,
        acao="lote_conjunto_estornado",
        objeto=lote,
        metadados={"movimentacao_estorno": movimento.pk, "motivo": motivo.strip()},
    )
    return lote


def resumo_transportes(lote):
    cargas = CargaLoteConjunto.objects.filter(lote=lote)
    total = cargas.aggregate(total=Sum("peso_liquido_kg"))["total"] or Decimal("0")
    quantidade = cargas.count()
    por_motorista = list(
        cargas.values("motorista_id", "motorista__nome")
        .annotate(quantidade_kg=Sum("peso_liquido_kg"), viagens=Sum(1))
        .order_by("motorista__nome")
    )
    por_veiculo = list(
        cargas.values("veiculo_cavalo_id", "veiculo_cavalo__placa", "placa_cavalo_informada")
        .annotate(quantidade_kg=Sum("peso_liquido_kg"), viagens=Sum(1))
        .order_by("veiculo_cavalo__placa", "placa_cavalo_informada")
    )
    por_transportadora = list(
        cargas.values("transportadora_id", "transportadora__nome")
        .annotate(quantidade_kg=Sum("peso_liquido_kg"))
        .order_by("transportadora__nome")
    )
    return {
        "quantidade_cargas": quantidade,
        "peso_total_kg": total,
        "peso_medio_kg": total / quantidade if quantidade else Decimal("0"),
        "por_motorista": por_motorista,
        "por_veiculo": por_veiculo,
        "por_transportadora": por_transportadora,
    }

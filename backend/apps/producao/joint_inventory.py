from decimal import Decimal

from django.db import transaction

from apps.core.access import PAPEIS_GESTAO

from .grain_access import exigir_acesso_cadpro
from .grain_models import AuditoriaProducao, MovimentacaoGraos
from .grain_services import ProducaoError, registrar_movimentacao
from .joint_access import exigir_acesso_lote, exigir_acesso_participante
from .joint_calculations import quantizar
from .joint_models import (
    CadProLoteConjunto,
    LoteConjuntoProducao,
    MovimentacaoLoteConjunto,
    ParticipanteLoteConjunto,
    SaldoLoteConjunto,
)


def dados_auditaveis(objeto):
    dados = {}
    for campo in objeto._meta.concrete_fields:
        valor = getattr(objeto, campo.attname)
        if isinstance(valor, Decimal):
            valor = str(valor)
        elif hasattr(valor, "isoformat"):
            valor = valor.isoformat()
        dados[campo.name] = valor
    return dados


def auditar(*, usuario, acao, objeto, propriedade=None, anteriores=None, metadados=None):
    return AuditoriaProducao.objects.create(
        propriedade=propriedade,
        usuario=usuario,
        acao=acao,
        entidade=objeto._meta.label,
        entidade_id=objeto.pk,
        dados_anteriores=anteriores or {},
        dados_novos=dados_auditaveis(objeto),
        metadados=metadados or {},
    )


def saldo_bloqueado(lote, local):
    saldo, _ = SaldoLoteConjunto.objects.select_for_update().get_or_create(
        lote=lote,
        local_armazenagem=local,
        defaults={"quantidade_kg": Decimal("0")},
    )
    return saldo


def registrar_movimento_conjunto(
    *, usuario, lote, tipo, quantidade, local_origem=None, local_destino=None,
    participante=None, cadpro=None, motivo="", referencia_tipo="", referencia_id=None,
):
    quantidade = quantizar(quantidade)
    if quantidade <= 0:
        raise ProducaoError("A quantidade deve ser positiva.")
    origem = saldo_bloqueado(lote, local_origem) if local_origem else None
    destino = saldo_bloqueado(lote, local_destino) if local_destino else None
    origem_anterior = origem.quantidade_kg if origem else None
    destino_anterior = destino.quantidade_kg if destino else None
    if origem:
        posterior = quantizar(origem.quantidade_kg - quantidade)
        if posterior < 0:
            raise ProducaoError(
                f"Saldo conjunto insuficiente. Disponível: {origem.quantidade_kg} kg; solicitado: {quantidade} kg."
            )
        origem.quantidade_kg = posterior
        origem.full_clean()
        origem.save(update_fields=("quantidade_kg", "atualizado_em"))
    if destino:
        destino.quantidade_kg = quantizar(destino.quantidade_kg + quantidade)
        destino.full_clean()
        destino.save(update_fields=("quantidade_kg", "atualizado_em"))
    movimento = MovimentacaoLoteConjunto.objects.create(
        lote=lote,
        tipo=tipo,
        local_origem=local_origem,
        local_destino=local_destino,
        participante=participante,
        cadpro=cadpro,
        quantidade_kg=quantidade,
        saldo_origem_anterior=origem_anterior,
        saldo_origem_posterior=origem.quantidade_kg if origem else None,
        saldo_destino_anterior=destino_anterior,
        saldo_destino_posterior=destino.quantidade_kg if destino else None,
        referencia_tipo=referencia_tipo,
        referencia_id=referencia_id,
        motivo=motivo,
        criado_por=usuario,
    )
    auditar(
        usuario=usuario,
        acao="movimentacao_lote_conjunto",
        objeto=movimento,
        metadados={"lote": lote.codigo},
    )
    return movimento


@transaction.atomic
def distribuir_saldo_lote(lote, *, usuario, distribuicoes, metodo, justificativa=""):
    lote = LoteConjuntoProducao.objects.select_for_update().get(pk=lote.pk)
    exigir_acesso_lote(usuario, lote, papeis=PAPEIS_GESTAO)
    if lote.status not in {LoteConjuntoProducao.Status.CONFIRMADO, LoteConjuntoProducao.Status.ENCERRADO}:
        raise ProducaoError("Somente lotes confirmados podem ser distribuídos.")
    saldo = saldo_bloqueado(lote, lote.local_armazenagem)
    total = sum((quantizar(item["quantidade_kg"]) for item in distribuicoes), start=Decimal("0"))
    if total <= 0 or total > saldo.quantidade_kg:
        raise ProducaoError(
            f"Distribuição inválida. Saldo conjunto disponível: {saldo.quantidade_kg} kg."
        )
    if metodo == ParticipanteLoteConjunto.MetodoRateio.MANUAL and not justificativa.strip():
        raise ProducaoError("O rateio manual exige justificativa.")
    processadas = []
    for item in distribuicoes:
        participante = item["participante"]
        cadpro = item["cadpro"]
        quantidade = quantizar(item["quantidade_kg"])
        exigir_acesso_participante(usuario, participante, papeis=PAPEIS_GESTAO)
        exigir_acesso_cadpro(usuario, cadpro, papeis=PAPEIS_GESTAO)
        if participante.lote_id != lote.id or cadpro.propriedade_id != participante.propriedade_id:
            raise ProducaoError("Participante ou CAD/PRO não pertence ao lote informado.")
        vinculos_talhao = list(participante.talhoes.select_related("talhao"))
        talhao = vinculos_talhao[0].talhao if len(vinculos_talhao) == 1 else None
        movimento_graos = registrar_movimentacao(
            usuario=usuario,
            tipo=MovimentacaoGraos.Tipo.ENTRADA,
            propriedade=participante.propriedade,
            cadpro=cadpro,
            talhao=talhao,
            cultura=lote.cultura,
            safra=lote.safra,
            quantidade_kg=quantidade,
            local_destino=lote.local_armazenagem,
            referencia_tipo="lote_conjunto",
            referencia_id=lote.pk,
            motivo=justificativa,
        )
        registrar_movimento_conjunto(
            usuario=usuario,
            lote=lote,
            tipo=MovimentacaoLoteConjunto.Tipo.DISTRIBUICAO,
            quantidade=quantidade,
            local_origem=lote.local_armazenagem,
            participante=participante,
            cadpro=cadpro,
            motivo=justificativa,
            referencia_tipo="movimentacao_graos",
            referencia_id=movimento_graos.pk,
        )
        vinculo, _ = CadProLoteConjunto.objects.get_or_create(
            lote=lote,
            cadpro=cadpro,
            defaults={
                "participante": participante,
                "criado_por": usuario,
                "metodo_rateio": metodo,
                "justificativa": justificativa,
            },
        )
        vinculo.participante = participante
        vinculo.quantidade_atribuida_kg = quantizar(vinculo.quantidade_atribuida_kg + quantidade)
        vinculo.metodo_rateio = metodo
        vinculo.justificativa = justificativa
        vinculo.full_clean()
        vinculo.save()
        participante.quantidade_rateada_kg = quantizar(
            (participante.quantidade_rateada_kg or Decimal("0")) + quantidade
        )
        participante.metodo_rateio = metodo
        participante.justificativa_rateio = justificativa
        participante.save(
            update_fields=(
                "quantidade_rateada_kg",
                "metodo_rateio",
                "justificativa_rateio",
                "atualizado_em",
            )
        )
        processadas.append(vinculo)
    auditar(
        usuario=usuario,
        acao="lote_conjunto_rateado",
        objeto=lote,
        metadados={
            "metodo": metodo,
            "quantidade_kg": str(total),
            "cadpros": [item.cadpro_id for item in processadas],
            "justificativa": justificativa,
        },
    )
    return processadas

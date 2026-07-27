from django.db import transaction

from apps.core.access import PAPEIS_ADMINISTRACAO, PAPEIS_OPERACAO

from .grain_services import ProducaoError
from .joint_access import exigir_acesso_lote
from .joint_inventory import auditar, dados_auditaveis, registrar_movimento_conjunto
from .joint_models import MovimentacaoLoteConjunto, SaidaLoteConjunto


@transaction.atomic
def confirmar_saida_conjunta(saida, *, usuario):
    saida = SaidaLoteConjunto.objects.select_for_update().select_related(
        "lote", "local_armazenagem"
    ).get(pk=saida.pk)
    exigir_acesso_lote(usuario, saida.lote, papeis=PAPEIS_OPERACAO)
    if saida.status != SaidaLoteConjunto.Status.RASCUNHO:
        raise ProducaoError("Somente saídas em rascunho podem ser confirmadas.")
    saida.full_clean()
    movimento = registrar_movimento_conjunto(
        usuario=usuario,
        lote=saida.lote,
        tipo=MovimentacaoLoteConjunto.Tipo.SAIDA,
        quantidade=saida.quantidade_kg,
        local_origem=saida.local_armazenagem,
        motivo=saida.justificativa,
        referencia_tipo="saida_lote_conjunto",
        referencia_id=saida.pk,
    )
    anteriores = dados_auditaveis(saida)
    saida.movimentacao = movimento
    saida.status = SaidaLoteConjunto.Status.CONFIRMADA
    saida.save(update_fields=("movimentacao", "status", "atualizado_em"))
    auditar(
        usuario=usuario,
        acao="saida_lote_conjunto_confirmada",
        objeto=saida,
        anteriores=anteriores,
        metadados={"lote": saida.lote.codigo},
    )
    return saida


@transaction.atomic
def estornar_saida_conjunta(saida, *, usuario, motivo):
    saida = SaidaLoteConjunto.objects.select_for_update().select_related(
        "lote", "local_armazenagem", "movimentacao"
    ).get(pk=saida.pk)
    exigir_acesso_lote(usuario, saida.lote, papeis=PAPEIS_ADMINISTRACAO)
    if saida.status != SaidaLoteConjunto.Status.CONFIRMADA or not saida.movimentacao_id:
        raise ProducaoError("Somente saídas confirmadas podem ser estornadas.")
    if not motivo.strip():
        raise ProducaoError("O estorno exige justificativa.")
    if MovimentacaoLoteConjunto.objects.filter(estorno_de=saida.movimentacao).exists():
        raise ProducaoError("Esta saída já possui estorno.")
    movimento = registrar_movimento_conjunto(
        usuario=usuario,
        lote=saida.lote,
        tipo=MovimentacaoLoteConjunto.Tipo.ESTORNO,
        quantidade=saida.quantidade_kg,
        local_destino=saida.local_armazenagem,
        motivo=motivo,
        referencia_tipo="saida_lote_conjunto",
        referencia_id=saida.pk,
    )
    movimento.estorno_de = saida.movimentacao
    movimento.save(update_fields=("estorno_de",))
    anteriores = dados_auditaveis(saida)
    saida.status = SaidaLoteConjunto.Status.ESTORNADA
    saida.save(update_fields=("status", "atualizado_em"))
    auditar(
        usuario=usuario,
        acao="saida_lote_conjunto_estornada",
        objeto=saida,
        anteriores=anteriores,
        metadados={"motivo": motivo, "movimentacao_estorno": movimento.pk},
    )
    return saida

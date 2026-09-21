import hashlib
import logging
from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from apps.graos.models import MovimentacaoGraos
from apps.graos.services import registrar_movimentacao, saldo_lote
from apps.cadpro.models import CADProPropriedade, normalizar_codigo_cadpro

from .models import ConfirmacaoImportacao, LinhaImportacao, LoteImportacao


logger = logging.getLogger(__name__)


class ConfirmacaoImportacaoError(ValueError):
    def __init__(
        self,
        mensagem,
        *,
        codigo="confirmacao_rejeitada",
        detalhes=None,
        replay_idempotente=False,
        registrar_falha=True,
        marcar_lote_falhou=False,
    ):
        super().__init__(mensagem)
        self.codigo = codigo
        self.detalhes = detalhes or []
        self.replay_idempotente = replay_idempotente
        self.registrar_falha = registrar_falha
        self.marcar_lote_falhou = marcar_lote_falhou


TIPOS_MOVIMENTACAO = {
    LinhaImportacao.Tipo.PRODUCAO: MovimentacaoGraos.Tipo.ENTRADA,
    LinhaImportacao.Tipo.TERCEIROS: MovimentacaoGraos.Tipo.ENTRADA,
    LinhaImportacao.Tipo.SAIDA: MovimentacaoGraos.Tipo.SAIDA,
}
STATUS_ELEGIVEIS = {
    LoteImportacao.Status.CONCLUIDO,
    LoteImportacao.Status.PRONTO_PARA_CONFIRMACAO,
    LoteImportacao.Status.FALHOU,
}
UNIDADES_KG = {"kg", "quilo", "quilos", "quilograma", "quilogramas"}


def _quantidade_linha(linha):
    try:
        quantidade = Decimal(
            str(linha.dados_normalizados.get("peso_liquido_kg", ""))
        )
    except (InvalidOperation, TypeError):
        return None
    return quantidade if quantidade.is_finite() and quantidade > 0 else None


def _data_movimento_linha(linha):
    valor = linha.dados_normalizados.get("data")
    if isinstance(valor, date):
        return valor
    try:
        return date.fromisoformat(str(valor))
    except (TypeError, ValueError):
        return None


def _validar_linha(linha, hashes_repetidos):
    erros = []
    dados = linha.dados_normalizados
    if linha.status not in {
        LinhaImportacao.Status.VALIDA,
        LinhaImportacao.Status.ADVERTENCIA,
    }:
        erros.append("status da linha não é elegível")
    if linha.erros:
        erros.append("a linha possui erro bloqueante")
    if not linha.propriedade_id:
        erros.append("propriedade associada ausente")
    if not linha.lote_graos_id:
        erros.append("lote de grãos associado ausente")
    if linha.movimentacao_graos_id:
        erros.append("a linha já possui movimentação vinculada")
    if linha.tipo not in TIPOS_MOVIMENTACAO:
        erros.append("tipo de movimentação inválido")
    if not dados.get("cultura"):
        erros.append("cultura ausente")
    if not dados.get("safra"):
        erros.append("safra ausente")
    if not _data_movimento_linha(linha):
        erros.append("data da movimentação inválida ou ausente")
    if _quantidade_linha(linha) is None:
        erros.append("quantidade deve ser Decimal positiva")

    unidade = str(dados.get("unidade", "kg")).strip().casefold()
    if unidade not in UNIDADES_KG:
        erros.append("unidade inválida; apenas quilogramas são suportados")

    if linha.lote_graos_id:
        lote_graos = linha.lote_graos
        if (
            linha.propriedade_id
            and lote_graos.propriedade_id != linha.propriedade_id
        ):
            erros.append("lote de grãos pertence a outra propriedade")
        if not lote_graos.ativo or not lote_graos.armazem.ativo:
            erros.append("lote de grãos e armazenagem precisam estar ativos")
        if not lote_graos.cad_pro_id or not lote_graos.cad_pro.ativo:
            erros.append("CAD/PRO ativo obrigatório")
        elif not CADProPropriedade.objects.filter(
            cad_pro_id=lote_graos.cad_pro_id,
            propriedade_id=linha.propriedade_id, ativo=True,
        ).exists():
            erros.append("vínculo ativo entre propriedade e CAD/PRO obrigatório")
        elif dados.get("cadpro_numero") and normalizar_codigo_cadpro(
            dados["cadpro_numero"]
        ) != lote_graos.cad_pro.codigo_normalizado:
            erros.append("CAD/PRO diverge do lote de grãos")
        if dados.get("classificacao_codigo", "PADRAO") != lote_graos.classificacao_codigo:
            erros.append("classificação diverge do lote de grãos")
        if str(dados.get("cultura", "")).strip().casefold() != (
            lote_graos.cultura.strip().casefold()
        ):
            erros.append("cultura diverge do lote de grãos")
        if str(dados.get("safra", "")).strip() != lote_graos.safra:
            erros.append("safra diverge do lote de grãos")

    if linha.tipo == LinhaImportacao.Tipo.SAIDA:
        if not str(dados.get("destino", "")).strip():
            erros.append("destino obrigatório ausente")
    elif linha.tipo == LinhaImportacao.Tipo.PRODUCAO:
        if not str(dados.get("propriedade_nome", "")).strip():
            erros.append("origem obrigatória ausente")
    elif linha.tipo == LinhaImportacao.Tipo.TERCEIROS:
        if not str(dados.get("produtor", "")).strip():
            erros.append("origem obrigatória ausente")

    if linha.hash_linha in hashes_repetidos:
        erros.append("duplicidade funcional dentro do lote de importação")
    elif LinhaImportacao.objects.filter(
        hash_linha=linha.hash_linha,
        movimentacao_graos__isnull=False,
    ).exclude(pk=linha.pk).exists():
        erros.append("duplicidade funcional já confirmada")
    return erros


def _validar_lote(lote, linhas):
    if lote.status == LoteImportacao.Status.CONFIRMADO:
        raise ConfirmacaoImportacaoError(
            "O lote já foi confirmado com outra chave de idempotência.",
            codigo="lote_ja_confirmado",
        )
    if lote.total_erros or any(linha.erros for linha in linhas):
        raise ConfirmacaoImportacaoError(
            "O lote possui erros bloqueantes e não pode ser confirmado.",
            codigo="lote_com_erros",
        )
    if lote.status not in STATUS_ELEGIVEIS:
        raise ConfirmacaoImportacaoError(
            f"O lote no status '{lote.status}' não é elegível para confirmação.",
            codigo="lote_nao_elegivel",
        )
    if not linhas:
        raise ConfirmacaoImportacaoError(
            "O lote não possui linhas para confirmar.",
            codigo="lote_sem_linhas",
        )

    contagem_hashes = Counter(linha.hash_linha for linha in linhas)
    hashes_repetidos = {
        hash_linha
        for hash_linha, quantidade in contagem_hashes.items()
        if quantidade > 1
    }
    rejeitadas = []
    for linha in linhas:
        erros = _validar_linha(linha, hashes_repetidos)
        if erros:
            rejeitadas.append(
                {
                    "linha_id": linha.id,
                    "planilha": linha.planilha,
                    "linha_origem": linha.linha_origem,
                    "erros": erros,
                }
            )
    if rejeitadas:
        raise ConfirmacaoImportacaoError(
            "Uma ou mais linhas falharam nas validações bloqueantes.",
            codigo="linhas_invalidas",
            detalhes=rejeitadas,
        )


def _chave_movimentacao(lote_id, linha_id, idempotency_key):
    resumo = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()
    return f"importacao:{lote_id}:{linha_id}:{resumo}"


def _referencia_externa(lote, linha):
    return (
        f"Importação {lote.id} - {linha.planilha}!{linha.linha_origem}"
    )[:120]


def _observacoes(lote, linha):
    return (
        f"Arquivo: {lote.arquivo_nome}; SHA-256: {lote.arquivo_sha256}; "
        f"linha de importação: {linha.id}"
    )


def _resultado_replay(confirmacao):
    resultado = dict(confirmacao.resultado)
    resultado["replay_idempotente"] = True
    return resultado


@transaction.atomic
def _confirmar_atomicamente(*, lote_id, usuario, idempotency_key):
    lote = (
        LoteImportacao.objects.select_for_update(of=("self",))
        .select_related("confirmado_por")
        .get(pk=lote_id)
    )
    tentativa = ConfirmacaoImportacao.objects.filter(
        idempotency_key=idempotency_key
    ).first()
    if tentativa:
        if (
            tentativa.lote_importacao_id == lote.id
            and tentativa.status == ConfirmacaoImportacao.Status.CONFIRMADA
        ):
            return _resultado_replay(tentativa), True
        if tentativa.lote_importacao_id == lote.id:
            raise ConfirmacaoImportacaoError(
                tentativa.falha or "A tentativa anterior falhou.",
                codigo="tentativa_anterior_falhou",
                detalhes=tentativa.resultado.get("linhas_rejeitadas", []),
                replay_idempotente=True,
                registrar_falha=False,
            )
        raise ConfirmacaoImportacaoError(
            "A chave de idempotência já foi usada em outro lote.",
            codigo="idempotency_key_em_uso",
            registrar_falha=False,
        )

    linhas = list(
        LinhaImportacao.objects.select_for_update(of=("self",))
        .select_related(
            "propriedade",
            "lote_graos",
            "lote_graos__cad_pro",
            "lote_graos__armazem",
            "lote_graos__armazem__propriedade",
            "movimentacao_graos",
        )
        .filter(lote_importacao=lote)
        .order_by("sequencia", "id")
    )
    _validar_lote(lote, linhas)

    lote.status = LoteImportacao.Status.CONFIRMANDO
    lote.save(update_fields=("status",))
    movimentos = []
    lotes_afetados = {}
    for linha in linhas:
        movimento = registrar_movimentacao(
            usuario=usuario,
            tipo=TIPOS_MOVIMENTACAO[linha.tipo],
            lote=linha.lote_graos,
            quantidade_kg=_quantidade_linha(linha),
            data_movimento=_data_movimento_linha(linha),
            referencia_externa=_referencia_externa(lote, linha),
            observacoes=_observacoes(lote, linha),
            chave_idempotencia=_chave_movimentacao(
                lote.id,
                linha.id,
                idempotency_key,
            ),
        )
        linha.movimentacao_graos = movimento
        linha.save(update_fields=("movimentacao_graos",))
        movimentos.append(movimento)
        lotes_afetados[movimento.lote_id] = movimento.lote

    confirmado_em = timezone.now()
    lote.status = LoteImportacao.Status.CONFIRMADO
    lote.confirmado_por = usuario
    lote.confirmado_em = confirmado_em
    lote.metadados = {
        **lote.metadados,
        "gera_movimentacoes": True,
        "confirmacao_idempotency_key": idempotency_key,
    }
    lote.save(
        update_fields=(
            "status",
            "confirmado_por",
            "confirmado_em",
            "metadados",
        )
    )
    saldos = [
        {
            "lote_graos_id": lote_graos.id,
            "codigo": lote_graos.codigo,
            "saldo_kg": str(saldo_lote(lote_graos)),
        }
        for lote_graos in lotes_afetados.values()
    ]
    resultado = {
        "lote_id": lote.id,
        "status": lote.status,
        "idempotency_key": idempotency_key,
        "usuario_confirmador": usuario.get_username(),
        "confirmado_em": confirmado_em.isoformat(),
        "total_linhas": len(linhas),
        "total_movimentacoes_criadas": len(movimentos),
        "linhas_rejeitadas": 0,
        "movimentacoes_ids": [movimento.id for movimento in movimentos],
        "replay_idempotente": False,
        "saldos_afetados": saldos,
    }
    ConfirmacaoImportacao.objects.create(
        lote_importacao=lote,
        idempotency_key=idempotency_key,
        status=ConfirmacaoImportacao.Status.CONFIRMADA,
        usuario=usuario,
        resultado=resultado,
    )
    return resultado, False


def _registrar_falha(*, lote_id, usuario, idempotency_key, erro):
    with transaction.atomic():
        lote = LoteImportacao.objects.select_for_update().get(pk=lote_id)
        existente = ConfirmacaoImportacao.objects.filter(
            idempotency_key=idempotency_key
        ).first()
        if not existente:
            ConfirmacaoImportacao.objects.create(
                lote_importacao=lote,
                idempotency_key=idempotency_key,
                status=ConfirmacaoImportacao.Status.FALHOU,
                usuario=usuario,
                resultado={
                    "codigo": erro.codigo,
                    "linhas_rejeitadas": erro.detalhes,
                    "replay_idempotente": erro.replay_idempotente,
                },
                falha=str(erro),
            )
        if erro.marcar_lote_falhou and lote.status != LoteImportacao.Status.CONFIRMADO:
            lote.status = LoteImportacao.Status.FALHOU
            lote.save(update_fields=("status",))


def confirmar_lote_importacao(*, lote_id, usuario, idempotency_key):
    try:
        return _confirmar_atomicamente(
            lote_id=lote_id,
            usuario=usuario,
            idempotency_key=idempotency_key,
        )
    except ConfirmacaoImportacaoError as exc:
        if exc.registrar_falha:
            _registrar_falha(
                lote_id=lote_id,
                usuario=usuario,
                idempotency_key=idempotency_key,
                erro=exc,
            )
        raise
    except Exception as exc:
        logger.exception(
            "Falha intermediária ao confirmar o lote de importação %s.",
            lote_id,
        )
        erro = ConfirmacaoImportacaoError(
            "A confirmação falhou e todos os efeitos foram revertidos.",
            codigo="falha_intermediaria",
            marcar_lote_falhou=True,
        )
        _registrar_falha(
            lote_id=lote_id,
            usuario=usuario,
            idempotency_key=idempotency_key,
            erro=erro,
        )
        raise erro from exc

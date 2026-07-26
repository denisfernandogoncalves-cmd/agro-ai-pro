from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.core.access import PAPEIS_GESTAO, PAPEIS_OPERACAO
from apps.financeiro.models import LancamentoFinanceiro

from .grain_access import exigir_acesso_cadpro
from .grain_enterprise_models import (
    AuditoriaCadPro,
    NotaFiscalProducao,
    TransferenciaGraos,
)
from .grain_models import (
    AuditoriaProducao,
    ContratoProducao,
    EmbarqueProducao,
    MovimentacaoGraos,
    RecebimentoProducao,
)
from .grain_services import (
    ProducaoError,
    confirmar_embarque,
    confirmar_recebimento,
    estornar_embarque,
    estornar_recebimento,
    registrar_movimentacao,
)


def _serializar_objeto(objeto):
    dados = {}
    for campo in objeto._meta.concrete_fields:
        valor = getattr(objeto, campo.attname)
        if isinstance(valor, Decimal):
            valor = str(valor)
        elif hasattr(valor, "isoformat"):
            valor = valor.isoformat()
        dados[campo.name] = valor
    return dados


def registrar_auditoria_enterprise(
    *,
    usuario,
    acao,
    objeto,
    propriedade=None,
    cadpro=None,
    anteriores=None,
    metadados=None,
):
    propriedade = propriedade or getattr(objeto, "propriedade", None)
    cadpro = cadpro or getattr(objeto, "cadpro", None)
    auditoria = AuditoriaProducao.objects.create(
        propriedade=propriedade,
        usuario=usuario,
        acao=acao,
        entidade=objeto._meta.label,
        entidade_id=objeto.pk,
        dados_anteriores=anteriores or {},
        dados_novos=_serializar_objeto(objeto),
        metadados=metadados or {},
    )
    if cadpro:
        AuditoriaCadPro.objects.create(auditoria=auditoria, cadpro=cadpro)
    return auditoria


def _vincular_auditoria_existente(*, acao, objeto, cadpro):
    auditoria = (
        AuditoriaProducao.objects.filter(
            acao=acao,
            entidade=objeto._meta.label,
            entidade_id=objeto.pk,
        )
        .order_by("-id")
        .first()
    )
    if auditoria and cadpro:
        AuditoriaCadPro.objects.get_or_create(auditoria=auditoria, defaults={"cadpro": cadpro})
    return auditoria


def _papeis_movimentacao(tipo):
    if tipo in {
        MovimentacaoGraos.Tipo.AJUSTE_ENTRADA,
        MovimentacaoGraos.Tipo.AJUSTE_SAIDA,
        MovimentacaoGraos.Tipo.ESTORNO,
    }:
        return PAPEIS_GESTAO
    return PAPEIS_OPERACAO


@transaction.atomic
def registrar_movimentacao_segura(*, usuario, tipo, cadpro, **kwargs):
    exigir_acesso_cadpro(usuario, cadpro, papeis=_papeis_movimentacao(tipo))
    movimento = registrar_movimentacao(
        usuario=usuario,
        tipo=tipo,
        cadpro=cadpro,
        **kwargs,
    )
    _vincular_auditoria_existente(
        acao="movimentacao_criada",
        objeto=movimento,
        cadpro=cadpro,
    )
    return movimento


@transaction.atomic
def confirmar_recebimento_seguro(recebimento, *, usuario):
    exigir_acesso_cadpro(usuario, recebimento.cadpro, papeis=PAPEIS_OPERACAO)
    confirmado = confirmar_recebimento(recebimento, usuario=usuario)
    _vincular_auditoria_existente(
        acao="recebimento_confirmado",
        objeto=confirmado,
        cadpro=confirmado.cadpro,
    )
    if confirmado.movimentacao_id:
        _vincular_auditoria_existente(
            acao="movimentacao_criada",
            objeto=confirmado.movimentacao,
            cadpro=confirmado.cadpro,
        )
    return confirmado


@transaction.atomic
def estornar_recebimento_seguro(recebimento, *, usuario, motivo):
    exigir_acesso_cadpro(usuario, recebimento.cadpro, papeis=PAPEIS_GESTAO)
    estornado = estornar_recebimento(recebimento, usuario=usuario, motivo=motivo)
    _vincular_auditoria_existente(
        acao="recebimento_estornado",
        objeto=estornado,
        cadpro=estornado.cadpro,
    )
    return estornado


def _criar_notas_legadas(embarque, usuario):
    referencias = (
        (NotaFiscalProducao.Tipo.PRODUTOR, embarque.nota_produtor),
        (NotaFiscalProducao.Tipo.EMPRESA, embarque.nota_empresa),
    )
    for tipo, numero in referencias:
        numero = str(numero or "").strip()
        if not numero:
            continue
        nota, criada = NotaFiscalProducao.objects.get_or_create(
            propriedade=embarque.propriedade,
            cadpro=embarque.cadpro,
            embarque=embarque,
            tipo=tipo,
            numero=numero,
            serie="",
            defaults={
                "data_emissao": embarque.data.date(),
                "valor": embarque.valor_total,
                "criado_por": usuario,
            },
        )
        if criada:
            registrar_auditoria_enterprise(
                usuario=usuario,
                acao="nota_fiscal_criada_automaticamente",
                objeto=nota,
                cadpro=embarque.cadpro,
            )


def _atualizar_status_contrato(contrato):
    if not contrato:
        return
    embarcado = contrato.embarques.filter(
        status=EmbarqueProducao.Status.CONFIRMADO,
    ).aggregate(total=Sum("quantidade_kg"))["total"] or Decimal("0")
    novo_status = (
        ContratoProducao.Status.CONCLUIDO
        if embarcado >= contrato.quantidade_kg
        else ContratoProducao.Status.ABERTO
    )
    if contrato.status != ContratoProducao.Status.CANCELADO and contrato.status != novo_status:
        contrato.status = novo_status
        contrato.save(update_fields=("status", "atualizado_em"))


@transaction.atomic
def confirmar_embarque_seguro(embarque, *, usuario):
    exigir_acesso_cadpro(usuario, embarque.cadpro, papeis=PAPEIS_GESTAO)
    if not embarque.contrato_id:
        raise ProducaoError("Informe o contrato antes de confirmar o embarque.")
    if not str(embarque.nota_produtor or "").strip() and not str(embarque.nota_empresa or "").strip():
        raise ProducaoError("Informe ao menos uma nota fiscal antes de confirmar o embarque.")
    confirmado = confirmar_embarque(embarque, usuario=usuario)
    _criar_notas_legadas(confirmado, usuario)
    _atualizar_status_contrato(confirmado.contrato)
    _vincular_auditoria_existente(
        acao="embarque_confirmado",
        objeto=confirmado,
        cadpro=confirmado.cadpro,
    )
    if confirmado.movimentacao_id:
        _vincular_auditoria_existente(
            acao="movimentacao_criada",
            objeto=confirmado.movimentacao,
            cadpro=confirmado.cadpro,
        )
    return confirmado


@transaction.atomic
def estornar_embarque_seguro(embarque, *, usuario, motivo):
    exigir_acesso_cadpro(usuario, embarque.cadpro, papeis=PAPEIS_GESTAO)
    lancamento = embarque.lancamento_financeiro
    if lancamento and lancamento.status == LancamentoFinanceiro.Status.LIQUIDADO:
        raise ProducaoError(
            "O lançamento financeiro já foi liquidado. Reverta a liquidação antes de estornar o embarque."
        )
    estornado = estornar_embarque(embarque, usuario=usuario, motivo=motivo)
    _atualizar_status_contrato(estornado.contrato)
    _vincular_auditoria_existente(
        acao="embarque_estornado",
        objeto=estornado,
        cadpro=estornado.cadpro,
    )
    return estornado


@transaction.atomic
def confirmar_transferencia(transferencia, *, usuario):
    transferencia = (
        TransferenciaGraos.objects.select_for_update()
        .select_related(
            "propriedade_origem",
            "cadpro_origem__propriedade",
            "talhao_origem",
            "local_origem",
            "propriedade_destino",
            "cadpro_destino__propriedade",
            "talhao_destino",
            "local_destino",
            "cultura",
            "safra",
        )
        .get(pk=transferencia.pk)
    )
    papeis = (
        PAPEIS_GESTAO
        if transferencia.cadpro_origem_id != transferencia.cadpro_destino_id
        or transferencia.propriedade_origem_id != transferencia.propriedade_destino_id
        else PAPEIS_OPERACAO
    )
    exigir_acesso_cadpro(usuario, transferencia.cadpro_origem, papeis=papeis)
    exigir_acesso_cadpro(usuario, transferencia.cadpro_destino, papeis=papeis)
    if transferencia.status != TransferenciaGraos.Status.RASCUNHO:
        raise ProducaoError("Somente transferências em rascunho podem ser confirmadas.")
    transferencia.full_clean()

    movimento_saida = registrar_movimentacao_segura(
        usuario=usuario,
        tipo=MovimentacaoGraos.Tipo.SAIDA,
        propriedade=transferencia.propriedade_origem,
        cadpro=transferencia.cadpro_origem,
        talhao=transferencia.talhao_origem,
        cultura=transferencia.cultura,
        safra=transferencia.safra,
        quantidade_kg=transferencia.quantidade_kg,
        local_origem=transferencia.local_origem,
        referencia_tipo="transferencia_graos",
        referencia_id=transferencia.pk,
        motivo=transferencia.motivo or "Transferência entre contextos",
    )
    movimento_entrada = registrar_movimentacao_segura(
        usuario=usuario,
        tipo=MovimentacaoGraos.Tipo.ENTRADA,
        propriedade=transferencia.propriedade_destino,
        cadpro=transferencia.cadpro_destino,
        talhao=transferencia.talhao_destino,
        cultura=transferencia.cultura,
        safra=transferencia.safra,
        quantidade_kg=transferencia.quantidade_kg,
        local_destino=transferencia.local_destino,
        referencia_tipo="transferencia_graos",
        referencia_id=transferencia.pk,
        motivo=transferencia.motivo or "Transferência entre contextos",
    )
    anteriores = _serializar_objeto(transferencia)
    transferencia.movimento_saida = movimento_saida
    transferencia.movimento_entrada = movimento_entrada
    transferencia.status = TransferenciaGraos.Status.CONFIRMADA
    transferencia.confirmado_por = usuario
    transferencia.confirmado_em = timezone.now()
    transferencia.save(
        update_fields=(
            "movimento_saida",
            "movimento_entrada",
            "status",
            "confirmado_por",
            "confirmado_em",
            "atualizado_em",
        )
    )
    registrar_auditoria_enterprise(
        usuario=usuario,
        acao="transferencia_confirmada",
        objeto=transferencia,
        propriedade=transferencia.propriedade_origem,
        cadpro=transferencia.cadpro_origem,
        anteriores=anteriores,
        metadados={"cadpro_destino": transferencia.cadpro_destino_id},
    )
    return transferencia


@transaction.atomic
def estornar_transferencia(transferencia, *, usuario, motivo):
    transferencia = (
        TransferenciaGraos.objects.select_for_update()
        .select_related(
            "cadpro_origem__propriedade",
            "cadpro_destino__propriedade",
            "movimento_saida",
            "movimento_entrada",
        )
        .get(pk=transferencia.pk)
    )
    exigir_acesso_cadpro(usuario, transferencia.cadpro_origem, papeis=PAPEIS_GESTAO)
    exigir_acesso_cadpro(usuario, transferencia.cadpro_destino, papeis=PAPEIS_GESTAO)
    if transferencia.status != TransferenciaGraos.Status.CONFIRMADA:
        raise ProducaoError("Somente transferências confirmadas podem ser estornadas.")
    if not transferencia.movimento_saida_id or not transferencia.movimento_entrada_id:
        raise ProducaoError("A transferência não possui rastreabilidade completa.")

    registrar_movimentacao_segura(
        usuario=usuario,
        tipo=MovimentacaoGraos.Tipo.ESTORNO,
        propriedade=transferencia.propriedade_destino,
        cadpro=transferencia.cadpro_destino,
        talhao=transferencia.talhao_destino,
        cultura=transferencia.cultura,
        safra=transferencia.safra,
        quantidade_kg=transferencia.quantidade_kg,
        local_destino=transferencia.local_destino,
        estorno_de=transferencia.movimento_entrada,
        referencia_tipo="estorno_transferencia",
        referencia_id=transferencia.pk,
        motivo=motivo,
    )
    registrar_movimentacao_segura(
        usuario=usuario,
        tipo=MovimentacaoGraos.Tipo.ESTORNO,
        propriedade=transferencia.propriedade_origem,
        cadpro=transferencia.cadpro_origem,
        talhao=transferencia.talhao_origem,
        cultura=transferencia.cultura,
        safra=transferencia.safra,
        quantidade_kg=transferencia.quantidade_kg,
        local_origem=transferencia.local_origem,
        estorno_de=transferencia.movimento_saida,
        referencia_tipo="estorno_transferencia",
        referencia_id=transferencia.pk,
        motivo=motivo,
    )
    anteriores = _serializar_objeto(transferencia)
    transferencia.status = TransferenciaGraos.Status.ESTORNADA
    transferencia.save(update_fields=("status", "atualizado_em"))
    registrar_auditoria_enterprise(
        usuario=usuario,
        acao="transferencia_estornada",
        objeto=transferencia,
        propriedade=transferencia.propriedade_origem,
        cadpro=transferencia.cadpro_origem,
        anteriores=anteriores,
        metadados={"motivo": motivo, "cadpro_destino": transferencia.cadpro_destino_id},
    )
    return transferencia

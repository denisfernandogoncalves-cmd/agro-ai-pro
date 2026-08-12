import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from types import MappingProxyType

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Case, DecimalField, F, Sum, Value, When
from django.db.models.functions import Coalesce
from django.utils import timezone

from .events import publicar_apos_commit
from .models import (
    ArmazemGraos,
    LoteGraos,
    MovimentacaoGraos,
    OrigemSaldoGraos,
    PosicaoSaldoGraos,
    ReservaSaldoGraos,
)
from .selectors import selecionar_posicoes


ZERO = Decimal("0.000")
CAMPO_QUANTIDADE = DecimalField(max_digits=16, decimal_places=3)


def bloquear_cadpro_para_saldo(cad_pro_id):
    """Lock canônico que sincroniza créditos de saldo e inativação do CAD/PRO."""
    from apps.cadpro.models import CADPro

    return CADPro.objects.select_for_update().get(pk=cad_pro_id)


def _bloquear_cadpros_ativos_para_saldo(cad_pro_ids):
    bloqueados = {}
    for cad_pro_id in sorted(set(cad_pro_ids), key=str):
        cad_pro = bloquear_cadpro_para_saldo(cad_pro_id)
        if not cad_pro.ativo:
            raise SaldoGraosError("O CAD/PRO precisa estar ativo para receber saldo.")
        bloqueados[cad_pro.pk] = cad_pro
    return bloqueados


class SaldoGraosError(ValueError):
    codigo = "saldo_graos_invalido"


class SaldoGraosInsuficienteError(SaldoGraosError):
    codigo = "saldo_insuficiente"


class CapacidadeArmazemExcedidaError(SaldoGraosError):
    codigo = "capacidade_excedida"


class MovimentacaoGraosConflitanteError(SaldoGraosError):
    codigo = "idempotencia_conflitante"


class ReservaSaldoGraosInvalidaError(SaldoGraosError):
    codigo = "reserva_invalida"


@dataclass(frozen=True)
class OrigemSaldoDTO:
    id: str
    tipo: str
    chave_idempotencia: str
    referencia_externa: str
    hash_requisicao: str
    metadados: MappingProxyType
    criado_por_id: str
    criado_por_nome: str
    criado_em: str


@dataclass(frozen=True)
class PosicaoSaldoDTO:
    id: str
    cad_pro_id: str
    cad_pro_codigo: str
    cultura: str
    safra: str
    classificacao_codigo: str
    armazem_id: str
    armazem_nome: str
    propriedade_id: str
    saldo_fisico_kg: Decimal
    saldo_comprometido_kg: Decimal
    versao: str
    criado_em: str
    atualizado_em: str

    @property
    def pk(self):
        return self.id

    @property
    def saldo_disponivel_kg(self):
        return self.saldo_fisico_kg - self.saldo_comprometido_kg


@dataclass(frozen=True)
class MovimentacaoSaldoDTO:
    id: str
    tipo: str
    operacao: str
    lote_id: str
    lote_codigo: str
    cultura: str
    safra: str
    armazem_id: str
    propriedade_id: str
    posicao_id: str
    origem_id: str
    reserva_id: str | None
    estorno_de_id: str | None
    quantidade_kg: Decimal
    delta_fisico_kg: Decimal
    delta_comprometido_kg: Decimal
    snapshot_anterior: MappingProxyType
    snapshot_posterior: MappingProxyType
    data_movimento: str
    referencia_externa: str
    chave_idempotencia: str | None
    observacoes: str
    criado_por_id: str
    criado_por_nome: str
    criado_em: str

    @property
    def pk(self):
        return self.id


@dataclass(frozen=True)
class ReservaSaldoDTO:
    id: str
    posicao_id: str
    origem_id: str
    quantidade_kg: Decimal
    saldo_reservado_kg: Decimal
    referencia_externa: str
    status: str
    criado_por_id: str
    criado_em: str
    atualizado_em: str

    @property
    def pk(self):
        return self.id


@dataclass(frozen=True)
class ResultadoOperacaoSaldo:
    codigo: str
    origem: OrigemSaldoDTO
    posicoes: tuple[PosicaoSaldoDTO, ...] = field(default_factory=tuple)
    movimentacoes: tuple[MovimentacaoSaldoDTO, ...] = field(default_factory=tuple)
    reserva: ReservaSaldoDTO | None = None
    idempotente: bool = False
    detalhes: MappingProxyType = field(default_factory=lambda: MappingProxyType({}))


def _congelar(valor):
    if isinstance(valor, dict):
        return MappingProxyType(
            {chave: _congelar(item) for chave, item in valor.items()}
        )
    if isinstance(valor, (list, tuple)):
        return tuple(_congelar(item) for item in valor)
    if isinstance(valor, set):
        return frozenset(_congelar(item) for item in valor)
    return valor


def _decimal(valor, *, permite_zero=False, permite_negativo=False):
    try:
        numero = Decimal(str(valor)).quantize(Decimal("0.001"))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise SaldoGraosError("Quantidade inválida.") from exc
    if not permite_negativo and numero < 0:
        raise SaldoGraosError("A quantidade não pode ser negativa.")
    if not permite_zero and numero == 0:
        raise SaldoGraosError("A quantidade deve ser diferente de zero.")
    return numero


def _quantidade_positiva(valor):
    numero = _decimal(valor)
    if numero <= 0:
        raise SaldoGraosError("A quantidade deve ser maior que zero.")
    return numero


def _valor_json(valor):
    if hasattr(valor, "pk"):
        return str(valor.pk)
    if isinstance(valor, (Decimal, date)):
        return str(valor)
    if isinstance(valor, dict):
        return {chave: _valor_json(item) for chave, item in sorted(valor.items())}
    if isinstance(valor, (list, tuple)):
        return [_valor_json(item) for item in valor]
    return valor


def _hash_requisicao(tipo, payload):
    serializado = json.dumps(
        {"tipo": tipo, "payload": _valor_json(payload)},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serializado.encode("utf-8")).hexdigest()


def _validar_chave(chave):
    chave = str(chave or "").strip()
    if not chave:
        raise SaldoGraosError("A chave de idempotência é obrigatória.")
    if len(chave) > 160:
        raise SaldoGraosError("A chave de idempotência deve ter até 160 caracteres.")
    return chave


def _texto_data(valor):
    return valor.isoformat() if valor else ""


def _origem_dto(origem):
    return OrigemSaldoDTO(
        id=str(origem.pk),
        tipo=str(origem.tipo),
        chave_idempotencia=origem.chave_idempotencia,
        referencia_externa=origem.referencia_externa,
        hash_requisicao=origem.hash_requisicao,
        metadados=_congelar(
            {
                chave: valor
                for chave, valor in origem.metadados.items()
                if not chave.startswith("_")
            }
        ),
        criado_por_id=str(origem.criado_por_id),
        criado_por_nome=origem.criado_por.username,
        criado_em=_texto_data(origem.criado_em),
    )


def _posicao_dto(posicao):
    return PosicaoSaldoDTO(
        id=str(posicao.pk),
        cad_pro_id=str(posicao.cad_pro_id),
        cad_pro_codigo=posicao.cad_pro.codigo,
        cultura=posicao.cultura,
        safra=posicao.safra,
        classificacao_codigo=posicao.classificacao_codigo,
        armazem_id=str(posicao.armazem_id),
        armazem_nome=posicao.armazem.nome,
        propriedade_id=str(posicao.armazem.propriedade_id),
        saldo_fisico_kg=posicao.saldo_fisico_kg,
        saldo_comprometido_kg=posicao.saldo_comprometido_kg,
        versao=str(posicao.versao),
        criado_em=_texto_data(posicao.criado_em),
        atualizado_em=_texto_data(posicao.atualizado_em),
    )


def _movimentacao_dto(movimento):
    return MovimentacaoSaldoDTO(
        id=str(movimento.pk),
        tipo=str(movimento.tipo),
        operacao=str(movimento.operacao),
        lote_id=str(movimento.lote_id),
        lote_codigo=movimento.lote.codigo,
        cultura=movimento.lote.cultura,
        safra=movimento.lote.safra,
        armazem_id=str(movimento.lote.armazem_id),
        propriedade_id=str(movimento.lote.armazem.propriedade_id),
        posicao_id=str(movimento.posicao_id),
        origem_id=str(movimento.origem_id),
        reserva_id=str(movimento.reserva_id) if movimento.reserva_id else None,
        estorno_de_id=(
            str(movimento.estorno_de_id) if movimento.estorno_de_id else None
        ),
        quantidade_kg=movimento.quantidade_kg,
        delta_fisico_kg=movimento.delta_fisico_kg,
        delta_comprometido_kg=movimento.delta_comprometido_kg,
        snapshot_anterior=_congelar(movimento.snapshot_anterior),
        snapshot_posterior=_congelar(movimento.snapshot_posterior),
        data_movimento=_texto_data(movimento.data_movimento),
        referencia_externa=movimento.referencia_externa,
        chave_idempotencia=movimento.chave_idempotencia,
        observacoes=movimento.observacoes,
        criado_por_id=str(movimento.criado_por_id),
        criado_por_nome=movimento.criado_por.username,
        criado_em=_texto_data(movimento.criado_em),
    )


def _reserva_dto(reserva):
    if not reserva:
        return None
    return ReservaSaldoDTO(
        id=str(reserva.pk),
        posicao_id=str(reserva.posicao_id),
        origem_id=str(reserva.origem_id),
        quantidade_kg=reserva.quantidade_kg,
        saldo_reservado_kg=reserva.saldo_reservado_kg,
        referencia_externa=reserva.referencia_externa,
        status=str(reserva.status),
        criado_por_id=str(reserva.criado_por_id),
        criado_em=_texto_data(reserva.criado_em),
        atualizado_em=_texto_data(reserva.atualizado_em),
    )


def _dto_para_payload(valor):
    if isinstance(valor, MappingProxyType) or hasattr(valor, "items"):
        return {chave: _dto_para_payload(item) for chave, item in valor.items()}
    if isinstance(valor, tuple):
        return [_dto_para_payload(item) for item in valor]
    if isinstance(valor, Decimal):
        return str(valor)
    if hasattr(valor, "__dataclass_fields__"):
        return {
            nome: _dto_para_payload(getattr(valor, nome))
            for nome in valor.__dataclass_fields__
        }
    return valor


def _resultado_do_payload(payload, *, idempotente):
    origem = payload["origem"]
    posicoes = payload.get("posicoes", ())
    movimentos = payload.get("movimentacoes", ())
    reserva = payload.get("reserva")
    return ResultadoOperacaoSaldo(
        codigo=payload["codigo"],
        origem=OrigemSaldoDTO(
            **{**origem, "metadados": _congelar(origem.get("metadados", {}))}
        ),
        posicoes=tuple(
            PosicaoSaldoDTO(
                **{
                    **item,
                    "saldo_fisico_kg": Decimal(item["saldo_fisico_kg"]),
                    "saldo_comprometido_kg": Decimal(
                        item["saldo_comprometido_kg"]
                    ),
                }
            )
            for item in posicoes
        ),
        movimentacoes=tuple(
            MovimentacaoSaldoDTO(
                **{
                    **item,
                    "quantidade_kg": Decimal(item["quantidade_kg"]),
                    "delta_fisico_kg": Decimal(item["delta_fisico_kg"]),
                    "delta_comprometido_kg": Decimal(
                        item["delta_comprometido_kg"]
                    ),
                    "snapshot_anterior": _congelar(item["snapshot_anterior"]),
                    "snapshot_posterior": _congelar(item["snapshot_posterior"]),
                }
            )
            for item in movimentos
        ),
        reserva=(
            ReservaSaldoDTO(
                **{
                    **reserva,
                    "quantidade_kg": Decimal(reserva["quantidade_kg"]),
                    "saldo_reservado_kg": Decimal(reserva["saldo_reservado_kg"]),
                }
            )
            if reserva
            else None
        ),
        idempotente=idempotente,
        detalhes=_congelar(payload.get("detalhes", {})),
    )


def _resultado_existente(origem, codigo):
    payload = origem.metadados.get("_resultado_original")
    if not payload:
        raise SaldoGraosError(
            f"A operação idempotente {codigo} não possui resultado persistido."
        )
    return _resultado_do_payload(payload, idempotente=True)


def _obter_ou_criar_origem(*, usuario, tipo, chave, payload, referencia="", metadados=None):
    chave = _validar_chave(chave)
    hash_requisicao = _hash_requisicao(
        tipo,
        {"dados": payload, "metadados": metadados or {}},
    )
    existente = OrigemSaldoGraos.objects.filter(chave_idempotencia=chave).first()
    if existente:
        if existente.tipo != tipo or existente.hash_requisicao != hash_requisicao:
            raise MovimentacaoGraosConflitanteError(
                "A chave de idempotência já foi usada com outro conteúdo."
            )
        return existente, False
    try:
        with transaction.atomic():
            origem = OrigemSaldoGraos.objects.create(
                tipo=tipo,
                chave_idempotencia=chave,
                referencia_externa=str(referencia or "").strip(),
                hash_requisicao=hash_requisicao,
                metadados=metadados or {},
                criado_por=usuario,
            )
    except IntegrityError:
        origem = OrigemSaldoGraos.objects.get(chave_idempotencia=chave)
        if origem.tipo != tipo or origem.hash_requisicao != hash_requisicao:
            raise MovimentacaoGraosConflitanteError(
                "A chave de idempotência já foi usada com outro conteúdo."
            )
        return origem, False
    return origem, True


def _validar_estado_lote(lote):
    if not lote.ativo or not lote.armazem.ativo:
        raise SaldoGraosError("O lote e o armazém precisam estar ativos.")
    if not lote.cad_pro_id:
        raise SaldoGraosError("O lote deve estar normalizado com um CAD/PRO.")
    try:
        lote.full_clean()
    except ValidationError as exc:
        raise SaldoGraosError("; ".join(exc.messages)) from exc
    return lote


def _validar_lote(lote):
    lote = LoteGraos.objects.select_related("armazem", "cad_pro").get(pk=lote.pk)
    return _validar_estado_lote(lote)


def _bloquear_lote_para_aumento(lote):
    cad_pro_id_recebido = lote.cad_pro_id
    referencia = LoteGraos.objects.only("cad_pro_id").get(pk=lote.pk)
    if cad_pro_id_recebido != referencia.cad_pro_id:
        raise SaldoGraosError(
            "O CAD/PRO do lote mudou desde a leitura. Atualize os dados e tente novamente."
        )
    if not referencia.cad_pro_id:
        raise SaldoGraosError("O lote deve estar normalizado com um CAD/PRO.")
    _bloquear_cadpros_ativos_para_saldo((referencia.cad_pro_id,))
    lote_bloqueado = LoteGraos.objects.select_for_update().get(pk=lote.pk)
    if lote_bloqueado.cad_pro_id != referencia.cad_pro_id:
        raise SaldoGraosError(
            "O CAD/PRO do lote mudou durante a operação. Tente novamente."
        )
    return _validar_estado_lote(lote_bloqueado)


def _validar_posicao_ativa(posicao):
    from apps.cadpro.models import CADProPropriedade

    posicao = PosicaoSaldoGraos.objects.select_related(
        "cad_pro", "armazem"
    ).get(pk=posicao.pk)
    if not posicao.cad_pro.ativo:
        raise SaldoGraosError("O CAD/PRO da posição precisa estar ativo.")
    if not posicao.armazem.ativo:
        raise SaldoGraosError("O armazém da posição precisa estar ativo.")
    if not CADProPropriedade.objects.filter(
        cad_pro_id=posicao.cad_pro_id,
        propriedade_id=posicao.armazem.propriedade_id,
        ativo=True,
        cad_pro__ativo=True,
    ).exists():
        raise SaldoGraosError(
            "O CAD/PRO deve possuir vínculo ativo com a propriedade do armazém."
        )
    return posicao


def _chave_posicao_lote(lote):
    return {
        "cad_pro_id": lote.cad_pro_id,
        "cultura": lote.cultura,
        "safra": lote.safra,
        "classificacao_codigo": lote.classificacao_codigo,
        "armazem_id": lote.armazem_id,
    }


def _bloquear_armazens(ids):
    ids = sorted(set(ids))
    return {
        item.pk: item
        for item in ArmazemGraos.objects.select_for_update()
        .filter(pk__in=ids)
        .order_by("pk")
    }


def _bloquear_posicoes_lotes(lotes):
    chaves = [_chave_posicao_lote(lote) for lote in lotes]
    ids = []
    for chave in chaves:
        posicao = PosicaoSaldoGraos.objects.filter(**chave).only("pk").first()
        if not posicao:
            try:
                with transaction.atomic():
                    posicao = PosicaoSaldoGraos.objects.create(**chave)
            except IntegrityError:
                posicao = PosicaoSaldoGraos.objects.only("pk").get(**chave)
        ids.append(posicao.pk)
    bloqueadas = {
        item.pk: item
        for item in PosicaoSaldoGraos.objects.select_for_update()
        .filter(pk__in=ids)
        .order_by("pk")
    }
    return tuple(bloqueadas[item_id] for item_id in ids)


def _bloquear_posicao_lote(lote):
    return _bloquear_posicoes_lotes((lote,))[0]


def _bloquear_contexto_reserva(reserva_id):
    referencia = ReservaSaldoGraos.objects.select_related("posicao").get(pk=reserva_id)
    _bloquear_armazens((referencia.posicao.armazem_id,))
    posicao = PosicaoSaldoGraos.objects.select_for_update().get(
        pk=referencia.posicao_id
    )
    reserva = ReservaSaldoGraos.objects.select_for_update().get(pk=reserva_id)
    if reserva.posicao_id != posicao.pk:
        raise ReservaSaldoGraosInvalidaError(
            "A reserva mudou de posição durante a operação."
        )
    return posicao, reserva


def _ocupacao_armazem_bloqueada(armazem_id):
    return PosicaoSaldoGraos.objects.filter(armazem_id=armazem_id).aggregate(
        total=Coalesce(
            Sum("saldo_fisico_kg"),
            Value(ZERO),
            output_field=CAMPO_QUANTIDADE,
        )
    )["total"]


def _aplicar_delta(posicao, *, fisico=ZERO, comprometido=ZERO):
    anterior = _snapshot_posicao(posicao)
    novo_fisico = posicao.saldo_fisico_kg + fisico
    novo_comprometido = posicao.saldo_comprometido_kg + comprometido
    if novo_fisico < 0:
        raise SaldoGraosInsuficienteError(
            f"Saldo físico insuficiente. Atual: {posicao.saldo_fisico_kg} kg."
        )
    if novo_comprometido < 0:
        raise ReservaSaldoGraosInvalidaError(
            "O saldo comprometido não pode ficar negativo."
        )
    if novo_comprometido > novo_fisico:
        raise SaldoGraosInsuficienteError(
            f"Saldo disponível insuficiente. Atual: {posicao.saldo_disponivel_kg} kg."
        )
    posicao.saldo_fisico_kg = novo_fisico
    posicao.saldo_comprometido_kg = novo_comprometido
    posicao.versao = F("versao") + 1
    posicao.save(
        update_fields=(
            "saldo_fisico_kg",
            "saldo_comprometido_kg",
            "versao",
            "atualizado_em",
        )
    )
    posicao.refresh_from_db()
    return anterior, _snapshot_posicao(posicao)


def _snapshot_posicao(posicao):
    return {
        "posicao_id": posicao.pk,
        "saldo_fisico_kg": str(posicao.saldo_fisico_kg),
        "saldo_comprometido_kg": str(posicao.saldo_comprometido_kg),
        "saldo_disponivel_kg": str(posicao.saldo_disponivel_kg),
        "versao": posicao.versao,
    }


def _criar_movimento(
    *,
    usuario,
    lote,
    posicao,
    origem,
    operacao,
    delta_fisico=ZERO,
    delta_comprometido=ZERO,
    reserva=None,
    estorno_de=None,
    data_movimento=None,
    referencia_externa="",
    observacoes="",
    chave_legada=None,
    snapshot_anterior=None,
    snapshot_posterior=None,
):
    quantidade = max(abs(delta_fisico), abs(delta_comprometido))
    tipo = (
        MovimentacaoGraos.Tipo.ENTRADA
        if delta_fisico > 0 or (delta_fisico == 0 and delta_comprometido > 0)
        else MovimentacaoGraos.Tipo.SAIDA
    )
    movimento = MovimentacaoGraos(
        tipo=tipo,
        operacao=operacao,
        lote=lote,
        posicao=posicao,
        origem=origem,
        reserva=reserva,
        estorno_de=estorno_de,
        quantidade_kg=quantidade,
        delta_fisico_kg=delta_fisico,
        delta_comprometido_kg=delta_comprometido,
        snapshot_anterior=snapshot_anterior or {},
        snapshot_posterior=snapshot_posterior or {},
        data_movimento=data_movimento or timezone.localdate(),
        referencia_externa=str(referencia_externa or "").strip(),
        chave_idempotencia=chave_legada,
        observacoes=observacoes or "",
        criado_por=usuario,
    )
    movimento.full_clean()
    movimento.save()
    return movimento


def _finalizar(codigo, origem, posicoes, movimentos=(), reserva=None, detalhes=None):
    posicoes = tuple(posicoes)
    movimentos = tuple(movimentos)
    detalhes_congelados = _congelar(_valor_json(detalhes or {}))
    resultado = ResultadoOperacaoSaldo(
        codigo=codigo,
        origem=_origem_dto(origem),
        posicoes=tuple(_posicao_dto(item) for item in posicoes),
        movimentacoes=tuple(_movimentacao_dto(item) for item in movimentos),
        reserva=_reserva_dto(reserva),
        detalhes=detalhes_congelados,
    )
    metadados = {
        **origem.metadados,
        "_resultado_original": _dto_para_payload(resultado),
    }
    OrigemSaldoGraos.objects.filter(pk=origem.pk).update(metadados=metadados)
    publicar_apos_commit(
        nome=codigo,
        origem=origem,
        posicoes=posicoes,
        movimentos=movimentos,
        reserva=reserva,
    )
    return resultado


@transaction.atomic
def creditar_producao(
    *, usuario, lote, quantidade_kg, chave_idempotencia, data_movimento=None,
    referencia_externa="", observacoes="", metadados=None,
):
    quantidade = _quantidade_positiva(quantidade_kg)
    payload = {"lote": lote, "quantidade_kg": quantidade, "data": data_movimento,
               "referencia": referencia_externa, "observacoes": observacoes}
    origem, criada = _obter_ou_criar_origem(
        usuario=usuario, tipo=OrigemSaldoGraos.Tipo.PRODUCAO,
        chave=chave_idempotencia, payload=payload, referencia=referencia_externa,
        metadados=metadados,
    )
    if not criada:
        return _resultado_existente(origem, "producao_creditada")
    lote = _bloquear_lote_para_aumento(lote)
    armazem = _bloquear_armazens((lote.armazem_id,))[lote.armazem_id]
    posicao = _bloquear_posicao_lote(lote)
    ocupacao = _ocupacao_armazem_bloqueada(armazem.pk)
    if ocupacao + quantidade > armazem.capacidade_kg:
        raise CapacidadeArmazemExcedidaError(
            f"Capacidade insuficiente. Disponível: {armazem.capacidade_kg - ocupacao} kg."
        )
    anterior, posterior = _aplicar_delta(posicao, fisico=quantidade)
    movimento = _criar_movimento(
        usuario=usuario, lote=lote, posicao=posicao, origem=origem,
        operacao=MovimentacaoGraos.Operacao.CREDITO_PRODUCAO,
        delta_fisico=quantidade, data_movimento=data_movimento,
        referencia_externa=referencia_externa, observacoes=observacoes,
        snapshot_anterior=anterior, snapshot_posterior=posterior,
    )
    return _finalizar("producao_creditada", origem, (posicao,), (movimento,))


@transaction.atomic
def reservar_saldo(
    *, usuario, lote, quantidade_kg, chave_idempotencia,
    referencia_externa="", observacoes="", metadados=None,
):
    quantidade = _quantidade_positiva(quantidade_kg)
    payload = {"lote": lote, "quantidade_kg": quantidade,
               "referencia": referencia_externa, "observacoes": observacoes}
    origem, criada = _obter_ou_criar_origem(
        usuario=usuario, tipo=OrigemSaldoGraos.Tipo.RESERVA,
        chave=chave_idempotencia, payload=payload, referencia=referencia_externa,
        metadados=metadados,
    )
    if not criada:
        return _resultado_existente(origem, "saldo_reservado")
    lote = _validar_lote(lote)
    _bloquear_armazens((lote.armazem_id,))
    posicao = _bloquear_posicao_lote(lote)
    anterior, posterior = _aplicar_delta(posicao, comprometido=quantidade)
    reserva = ReservaSaldoGraos.objects.create(
        posicao=posicao, origem=origem, quantidade_kg=quantidade,
        saldo_reservado_kg=quantidade, referencia_externa=referencia_externa,
        criado_por=usuario,
    )
    movimento = _criar_movimento(
        usuario=usuario, lote=lote, posicao=posicao, origem=origem,
        operacao=MovimentacaoGraos.Operacao.RESERVA,
        delta_comprometido=quantidade, reserva=reserva, observacoes=observacoes,
        referencia_externa=referencia_externa,
        snapshot_anterior=anterior, snapshot_posterior=posterior,
    )
    return _finalizar("saldo_reservado", origem, (posicao,), (movimento,), reserva)


def _status_reserva(reserva, *, liberacao=False):
    if reserva.saldo_reservado_kg > 0:
        return ReservaSaldoGraos.Status.PARCIAL
    return (
        ReservaSaldoGraos.Status.LIBERADA
        if liberacao
        else ReservaSaldoGraos.Status.CONCLUIDA
    )


def _lote_da_posicao(posicao):
    lote = LoteGraos.objects.filter(
        cad_pro_id=posicao.cad_pro_id,
        cultura=posicao.cultura,
        safra=posicao.safra,
        classificacao_codigo=posicao.classificacao_codigo,
        armazem_id=posicao.armazem_id,
        ativo=True,
    ).order_by("id").first()
    if not lote:
        raise SaldoGraosError("Nenhum lote ativo representa a posição informada.")
    return lote


@transaction.atomic
def liberar_reserva(
    *, usuario, reserva, chave_idempotencia, quantidade_kg=None,
    referencia_externa="", observacoes="", metadados=None,
):
    reserva_id = reserva.pk
    quantidade_informada = quantidade_kg
    payload = {"reserva": reserva_id, "quantidade_kg": quantidade_informada,
               "referencia": referencia_externa, "observacoes": observacoes}
    origem, criada = _obter_ou_criar_origem(
        usuario=usuario, tipo=OrigemSaldoGraos.Tipo.LIBERACAO,
        chave=chave_idempotencia, payload=payload, referencia=referencia_externa,
        metadados=metadados,
    )
    if not criada:
        return _resultado_existente(origem, "reserva_liberada")
    posicao, reserva = _bloquear_contexto_reserva(reserva_id)
    quantidade = (
        reserva.saldo_reservado_kg
        if quantidade_informada is None
        else _quantidade_positiva(quantidade_informada)
    )
    if quantidade > reserva.saldo_reservado_kg:
        raise ReservaSaldoGraosInvalidaError("A liberação excede o saldo da reserva.")
    _validar_posicao_ativa(posicao)
    lote = _lote_da_posicao(posicao)
    anterior, posterior = _aplicar_delta(posicao, comprometido=-quantidade)
    reserva.saldo_reservado_kg -= quantidade
    reserva.status = _status_reserva(reserva, liberacao=True)
    reserva.save(update_fields=("saldo_reservado_kg", "status", "atualizado_em"))
    movimento = _criar_movimento(
        usuario=usuario, lote=lote, posicao=posicao, origem=origem,
        operacao=MovimentacaoGraos.Operacao.LIBERACAO,
        delta_comprometido=-quantidade, reserva=reserva,
        referencia_externa=referencia_externa, observacoes=observacoes,
        snapshot_anterior=anterior, snapshot_posterior=posterior,
    )
    return _finalizar("reserva_liberada", origem, (posicao,), (movimento,), reserva)


@transaction.atomic
def confirmar_entrega(
    *, usuario, reserva, chave_idempotencia, quantidade_kg=None,
    data_movimento=None, referencia_externa="", observacoes="", metadados=None,
):
    reserva_id = reserva.pk
    payload = {"reserva": reserva_id, "quantidade_kg": quantidade_kg,
               "data": data_movimento, "referencia": referencia_externa,
               "observacoes": observacoes}
    origem, criada = _obter_ou_criar_origem(
        usuario=usuario, tipo=OrigemSaldoGraos.Tipo.ENTREGA,
        chave=chave_idempotencia, payload=payload, referencia=referencia_externa,
        metadados=metadados,
    )
    if not criada:
        return _resultado_existente(origem, "entrega_confirmada")
    posicao, reserva = _bloquear_contexto_reserva(reserva_id)
    quantidade = (
        reserva.saldo_reservado_kg
        if quantidade_kg is None
        else _quantidade_positiva(quantidade_kg)
    )
    if quantidade > reserva.saldo_reservado_kg:
        raise ReservaSaldoGraosInvalidaError("A entrega excede o saldo da reserva.")
    _validar_posicao_ativa(posicao)
    lote = _lote_da_posicao(posicao)
    anterior, posterior = _aplicar_delta(
        posicao, fisico=-quantidade, comprometido=-quantidade
    )
    reserva.saldo_reservado_kg -= quantidade
    reserva.status = _status_reserva(reserva)
    reserva.save(update_fields=("saldo_reservado_kg", "status", "atualizado_em"))
    movimento = _criar_movimento(
        usuario=usuario, lote=lote, posicao=posicao, origem=origem,
        operacao=MovimentacaoGraos.Operacao.ENTREGA,
        delta_fisico=-quantidade, delta_comprometido=-quantidade,
        reserva=reserva, data_movimento=data_movimento,
        referencia_externa=referencia_externa, observacoes=observacoes,
        snapshot_anterior=anterior, snapshot_posterior=posterior,
    )
    return _finalizar("entrega_confirmada", origem, (posicao,), (movimento,), reserva)


@transaction.atomic
def registrar_devolucao(
    *, usuario, lote, quantidade_kg, chave_idempotencia, data_movimento=None,
    referencia_externa="", observacoes="", metadados=None,
):
    quantidade = _quantidade_positiva(quantidade_kg)
    payload = {"lote": lote, "quantidade_kg": quantidade, "data": data_movimento,
               "referencia": referencia_externa, "observacoes": observacoes}
    origem, criada = _obter_ou_criar_origem(
        usuario=usuario, tipo=OrigemSaldoGraos.Tipo.DEVOLUCAO,
        chave=chave_idempotencia, payload=payload, referencia=referencia_externa,
        metadados=metadados,
    )
    if not criada:
        return _resultado_existente(origem, "devolucao_registrada")
    lote = _bloquear_lote_para_aumento(lote)
    armazem = _bloquear_armazens((lote.armazem_id,))[lote.armazem_id]
    posicao = _bloquear_posicao_lote(lote)
    ocupacao = _ocupacao_armazem_bloqueada(armazem.pk)
    if ocupacao + quantidade > armazem.capacidade_kg:
        raise CapacidadeArmazemExcedidaError("A devolução excede a capacidade do armazém.")
    anterior, posterior = _aplicar_delta(posicao, fisico=quantidade)
    movimento = _criar_movimento(
        usuario=usuario, lote=lote, posicao=posicao, origem=origem,
        operacao=MovimentacaoGraos.Operacao.DEVOLUCAO,
        delta_fisico=quantidade, data_movimento=data_movimento,
        referencia_externa=referencia_externa, observacoes=observacoes,
        snapshot_anterior=anterior, snapshot_posterior=posterior,
    )
    return _finalizar("devolucao_registrada", origem, (posicao,), (movimento,))


@transaction.atomic
def registrar_ajuste(
    *, usuario, lote, delta_fisico_kg, chave_idempotencia,
    delta_comprometido_kg=ZERO, data_movimento=None,
    referencia_externa="", observacoes="", metadados=None,
):
    delta_fisico = _decimal(delta_fisico_kg, permite_zero=True, permite_negativo=True)
    delta_comprometido = _decimal(
        delta_comprometido_kg, permite_zero=True, permite_negativo=True
    )
    if delta_fisico == 0 and delta_comprometido == 0:
        raise SaldoGraosError("O ajuste deve alterar ao menos um saldo.")
    payload = {"lote": lote, "delta_fisico_kg": delta_fisico,
               "delta_comprometido_kg": delta_comprometido, "data": data_movimento,
               "referencia": referencia_externa, "observacoes": observacoes}
    origem, criada = _obter_ou_criar_origem(
        usuario=usuario, tipo=OrigemSaldoGraos.Tipo.AJUSTE,
        chave=chave_idempotencia, payload=payload, referencia=referencia_externa,
        metadados=metadados,
    )
    if not criada:
        return _resultado_existente(origem, "ajuste_registrado")
    if delta_fisico > 0:
        lote = _bloquear_lote_para_aumento(lote)
    else:
        lote = _validar_lote(lote)
    if delta_fisico > 0:
        armazem = _bloquear_armazens((lote.armazem_id,))[lote.armazem_id]
    else:
        _bloquear_armazens((lote.armazem_id,))
    posicao = _bloquear_posicao_lote(lote)
    if delta_fisico > 0:
        if (
            _ocupacao_armazem_bloqueada(armazem.pk) + delta_fisico
            > armazem.capacidade_kg
        ):
            raise CapacidadeArmazemExcedidaError(
                "O ajuste excede a capacidade do armazém."
            )
    anterior, posterior = _aplicar_delta(
        posicao, fisico=delta_fisico, comprometido=delta_comprometido
    )
    movimento = _criar_movimento(
        usuario=usuario, lote=lote, posicao=posicao, origem=origem,
        operacao=MovimentacaoGraos.Operacao.AJUSTE,
        delta_fisico=delta_fisico, delta_comprometido=delta_comprometido,
        data_movimento=data_movimento, referencia_externa=referencia_externa,
        observacoes=observacoes,
        snapshot_anterior=anterior, snapshot_posterior=posterior,
    )
    return _finalizar("ajuste_registrado", origem, (posicao,), (movimento,))


@transaction.atomic
def estornar_movimentacao(
    *, usuario, movimentacao, chave_idempotencia, data_movimento=None,
    referencia_externa="", observacoes="", metadados=None,
):
    movimento_id = movimentacao.pk
    payload = {"movimentacao": movimento_id, "data": data_movimento,
               "referencia": referencia_externa, "observacoes": observacoes}
    origem, criada = _obter_ou_criar_origem(
        usuario=usuario, tipo=OrigemSaldoGraos.Tipo.ESTORNO,
        chave=chave_idempotencia, payload=payload, referencia=referencia_externa,
        metadados=metadados,
    )
    if not criada:
        return _resultado_existente(origem, "movimentacao_estornada")
    movimento = MovimentacaoGraos.objects.select_related(
        "posicao", "lote", "reserva"
    ).get(pk=movimento_id)
    if movimento.operacao == MovimentacaoGraos.Operacao.ESTORNO:
        raise SaldoGraosError("Não é permitido estornar um estorno.")
    operacoes_transferencia = {
        MovimentacaoGraos.Operacao.TRANSFERENCIA_SAIDA,
        MovimentacaoGraos.Operacao.TRANSFERENCIA_ENTRADA,
    }
    if movimento.operacao in operacoes_transferencia:
        movimentos = tuple(
            MovimentacaoGraos.objects.select_related("posicao", "lote", "reserva")
            .filter(origem_id=movimento.origem_id, operacao__in=operacoes_transferencia)
            .order_by("posicao_id", "id")
        )
        if (
            len(movimentos) != 2
            or {item.operacao for item in movimentos} != operacoes_transferencia
            or sum((item.delta_fisico_kg for item in movimentos), ZERO) != ZERO
            or any(item.delta_comprometido_kg != ZERO for item in movimentos)
        ):
            raise SaldoGraosError(
                "A transferência não possui duas pernas íntegras para estorno."
            )
    else:
        movimentos = (movimento,)

    _bloquear_cadpros_ativos_para_saldo(
        item.posicao.cad_pro_id
        for item in movimentos
        if item.delta_fisico_kg < ZERO
    )

    ids_movimentos = tuple(item.pk for item in movimentos)
    ids_reservas = tuple(
        sorted({item.reserva_id for item in movimentos if item.reserva_id})
    )
    armazens_bloqueados = _bloquear_armazens(
        item.posicao.armazem_id for item in movimentos
    )

    posicoes_bloqueadas = {
        item.pk: item
        for item in PosicaoSaldoGraos.objects.select_for_update()
        .filter(pk__in={item.posicao_id for item in movimentos})
        .order_by("pk")
    }
    for posicao in posicoes_bloqueadas.values():
        _validar_posicao_ativa(posicao)
    reservas_bloqueadas = {
        item.pk: item
        for item in ReservaSaldoGraos.objects.select_for_update()
        .filter(pk__in=ids_reservas)
        .order_by("pk")
    }
    movimentos = tuple(
        MovimentacaoGraos.objects.select_for_update()
        .select_related("posicao", "lote", "lote__armazem")
        .filter(pk__in=ids_movimentos)
        .order_by("pk")
    )
    movimento = next(
        item for item in movimentos if str(item.pk) == str(movimento_id)
    )
    if MovimentacaoGraos.objects.filter(estorno_de_id__in=ids_movimentos).exists():
        raise SaldoGraosError("A movimentação já foi estornada.")

    acrescimos_por_armazem = {}
    reducoes_por_armazem = {}
    for item in movimentos:
        delta = -item.delta_fisico_kg
        armazem_id = item.posicao.armazem_id
        if delta > 0:
            acrescimos_por_armazem[armazem_id] = (
                acrescimos_por_armazem.get(armazem_id, ZERO) + delta
            )
        elif delta < 0:
            reducoes_por_armazem[armazem_id] = (
                reducoes_por_armazem.get(armazem_id, ZERO) - delta
            )
    for armazem_id, acrescimo in acrescimos_por_armazem.items():
        acrescimo_liquido = acrescimo - reducoes_por_armazem.get(armazem_id, ZERO)
        if acrescimo_liquido <= 0:
            continue
        armazem = armazens_bloqueados[armazem_id]
        if _ocupacao_armazem_bloqueada(armazem_id) + acrescimo_liquido > armazem.capacidade_kg:
            raise CapacidadeArmazemExcedidaError(
                "O estorno excede a capacidade do armazém."
            )

    reserva = reservas_bloqueadas.get(movimento.reserva_id)
    if reserva:
        reserva.saldo_reservado_kg -= movimento.delta_comprometido_kg
        if not ZERO <= reserva.saldo_reservado_kg <= reserva.quantidade_kg:
            raise ReservaSaldoGraosInvalidaError(
                "O estorno deixaria a reserva inconsistente."
            )
        reserva.status = (
            ReservaSaldoGraos.Status.ATIVA
            if reserva.saldo_reservado_kg == reserva.quantidade_kg
            else _status_reserva(reserva, liberacao=True)
        )
        reserva.save(update_fields=("saldo_reservado_kg", "status", "atualizado_em"))

    estornos = []
    for original in movimentos:
        posicao = posicoes_bloqueadas[original.posicao_id]
        delta_fisico = -original.delta_fisico_kg
        delta_comprometido = -original.delta_comprometido_kg
        anterior, posterior = _aplicar_delta(
            posicao,
            fisico=delta_fisico,
            comprometido=delta_comprometido,
        )
        estornos.append(
            _criar_movimento(
                usuario=usuario,
                lote=original.lote,
                posicao=posicao,
                origem=origem,
                operacao=MovimentacaoGraos.Operacao.ESTORNO,
                delta_fisico=delta_fisico,
                delta_comprometido=delta_comprometido,
                reserva=reserva,
                estorno_de=original,
                data_movimento=data_movimento,
                referencia_externa=referencia_externa,
                observacoes=observacoes,
                snapshot_anterior=anterior,
                snapshot_posterior=posterior,
            )
        )
    codigo = (
        "transferencia_estornada"
        if len(movimentos) == 2
        else "movimentacao_estornada"
    )
    return _finalizar(
        codigo,
        origem,
        tuple(posicoes_bloqueadas.values()),
        tuple(estornos),
        reserva,
    )


@transaction.atomic
def transferir_saldo_fisico(
    *, usuario, lote_origem, lote_destino, quantidade_kg, chave_idempotencia,
    data_movimento=None, referencia_externa="", observacoes="", metadados=None,
):
    if lote_origem.pk == lote_destino.pk:
        raise SaldoGraosError("Os lotes de origem e destino devem ser diferentes.")
    quantidade = _quantidade_positiva(quantidade_kg)
    payload = {"lote_origem": lote_origem, "lote_destino": lote_destino,
               "quantidade_kg": quantidade, "data": data_movimento,
               "referencia": referencia_externa, "observacoes": observacoes}
    origem, criada = _obter_ou_criar_origem(
        usuario=usuario, tipo=OrigemSaldoGraos.Tipo.TRANSFERENCIA,
        chave=chave_idempotencia, payload=payload, referencia=referencia_externa,
        metadados=metadados,
    )
    if not criada:
        return _resultado_existente(origem, "saldo_transferido")
    try:
        destino_lote = _bloquear_lote_para_aumento(lote_destino)
    except LoteGraos.DoesNotExist as exc:
        raise SaldoGraosError(
            "Lote de origem ou destino não encontrado."
        ) from exc
    origem_lote = LoteGraos.objects.filter(pk=lote_origem.pk).first()
    if not origem_lote:
        raise SaldoGraosError("Lote de origem ou destino não encontrado.")
    origem_lote = _validar_lote(origem_lote)
    if (origem_lote.cultura, origem_lote.safra, origem_lote.classificacao_codigo) != (
        destino_lote.cultura, destino_lote.safra, destino_lote.classificacao_codigo
    ):
        raise SaldoGraosError("A transferência exige cultura, safra e classificação iguais.")
    armazens = _bloquear_armazens(
        (origem_lote.armazem_id, destino_lote.armazem_id)
    )
    pos_origem, pos_destino = _bloquear_posicoes_lotes(
        (origem_lote, destino_lote)
    )
    posicoes = (pos_origem, pos_destino)
    if quantidade > pos_origem.saldo_disponivel_kg:
        raise SaldoGraosInsuficienteError(
            f"Saldo disponível insuficiente. Atual: {pos_origem.saldo_disponivel_kg} kg."
        )
    if pos_destino.armazem_id != pos_origem.armazem_id:
        armazem_destino = armazens[pos_destino.armazem_id]
        ocupacao = _ocupacao_armazem_bloqueada(armazem_destino.pk)
        if ocupacao + quantidade > armazem_destino.capacidade_kg:
            raise CapacidadeArmazemExcedidaError("A transferência excede a capacidade do destino.")
    anterior_origem, posterior_origem = _aplicar_delta(
        pos_origem, fisico=-quantidade
    )
    anterior_destino, posterior_destino = _aplicar_delta(
        pos_destino, fisico=quantidade
    )
    saida = _criar_movimento(
        usuario=usuario, lote=origem_lote, posicao=pos_origem, origem=origem,
        operacao=MovimentacaoGraos.Operacao.TRANSFERENCIA_SAIDA,
        delta_fisico=-quantidade, data_movimento=data_movimento,
        referencia_externa=referencia_externa, observacoes=observacoes,
        snapshot_anterior=anterior_origem,
        snapshot_posterior=posterior_origem,
    )
    entrada = _criar_movimento(
        usuario=usuario, lote=destino_lote, posicao=pos_destino, origem=origem,
        operacao=MovimentacaoGraos.Operacao.TRANSFERENCIA_ENTRADA,
        delta_fisico=quantidade, data_movimento=data_movimento,
        referencia_externa=referencia_externa, observacoes=observacoes,
        snapshot_anterior=anterior_destino,
        snapshot_posterior=posterior_destino,
    )
    return _finalizar("saldo_transferido", origem, (pos_origem, pos_destino), (saida, entrada))


def consultar_posicao(**filtros):
    return selecionar_posicoes(**filtros)


@transaction.atomic
def reconciliar_posicao(*, usuario, posicao, chave_idempotencia, metadados=None):
    posicao_id = posicao.pk
    payload = {"posicao": posicao_id}
    origem, criada = _obter_ou_criar_origem(
        usuario=usuario, tipo=OrigemSaldoGraos.Tipo.RECONCILIACAO,
        chave=chave_idempotencia, payload=payload,
        metadados={**(metadados or {}), "_posicao_id": posicao_id},
    )
    if not criada:
        return _resultado_existente(origem, "posicao_reconciliada")
    referencia = PosicaoSaldoGraos.objects.only(
        "armazem_id",
        "cad_pro_id",
    ).get(pk=posicao_id)
    _bloquear_cadpros_ativos_para_saldo((referencia.cad_pro_id,))
    _bloquear_armazens((referencia.armazem_id,))
    posicao = PosicaoSaldoGraos.objects.select_for_update().get(pk=posicao_id)
    _validar_posicao_ativa(posicao)
    tuple(
        ReservaSaldoGraos.objects.select_for_update()
        .filter(posicao_id=posicao_id)
        .order_by("pk")
    )
    movimentos = tuple(
        MovimentacaoGraos.objects.select_for_update()
        .filter(posicao_id=posicao_id)
        .order_by("pk")
    )
    totais = {
        "fisico": sum((item.delta_fisico_kg for item in movimentos), ZERO),
        "comprometido": sum(
            (item.delta_comprometido_kg for item in movimentos), ZERO
        ),
    }
    antes = {"saldo_fisico_kg": str(posicao.saldo_fisico_kg),
             "saldo_comprometido_kg": str(posicao.saldo_comprometido_kg)}
    divergente = (
        posicao.saldo_fisico_kg != totais["fisico"]
        or posicao.saldo_comprometido_kg != totais["comprometido"]
    )
    if totais["fisico"] < 0 or not ZERO <= totais["comprometido"] <= totais["fisico"]:
        raise SaldoGraosError("O ledger possui saldos inválidos e não pode ser reconciliado.")
    if divergente:
        posicao.saldo_fisico_kg = totais["fisico"]
        posicao.saldo_comprometido_kg = totais["comprometido"]
        posicao.versao = F("versao") + 1
        posicao.save(update_fields=("saldo_fisico_kg", "saldo_comprometido_kg", "versao", "atualizado_em"))
        posicao.refresh_from_db()
    detalhes = {"divergente": divergente, "antes": antes,
                "depois": {"saldo_fisico_kg": str(totais["fisico"]),
                            "saldo_comprometido_kg": str(totais["comprometido"])}}
    return _finalizar("posicao_reconciliada", origem, (posicao,), detalhes=detalhes)


def _saldo_agregado(queryset):
    return queryset.aggregate(
        saldo=Coalesce(
            Sum(Case(
                When(tipo=MovimentacaoGraos.Tipo.ENTRADA, then=F("quantidade_kg")),
                default=-F("quantidade_kg"), output_field=CAMPO_QUANTIDADE,
            )),
            Value(ZERO), output_field=CAMPO_QUANTIDADE,
        )
    )["saldo"]


def saldo_lote(lote):
    if lote.movimentacoes.exclude(posicao__isnull=True).exists():
        return lote.movimentacoes.aggregate(
            saldo=Coalesce(
                Sum("delta_fisico_kg"),
                Value(ZERO),
                output_field=CAMPO_QUANTIDADE,
            )
        )["saldo"]
    return _saldo_agregado(lote.movimentacoes.all())


def saldo_armazem(armazem):
    materializado = PosicaoSaldoGraos.objects.filter(armazem=armazem).aggregate(
        saldo=Coalesce(Sum("saldo_fisico_kg"), Value(ZERO), output_field=CAMPO_QUANTIDADE)
    )["saldo"]
    if materializado:
        return materializado
    return _saldo_agregado(MovimentacaoGraos.objects.filter(lote__armazem=armazem))


@transaction.atomic
def registrar_movimentacao(*, usuario, tipo, lote, quantidade_kg, **dados):
    """Compatibilidade do endpoint legado; novas integrações devem usar os serviços públicos."""
    chave = dados.pop("chave_idempotencia", "")
    if tipo == MovimentacaoGraos.Tipo.ENTRADA:
        resultado = creditar_producao(
            usuario=usuario, lote=lote, quantidade_kg=quantidade_kg,
            chave_idempotencia=chave, **dados,
        )
    elif tipo == MovimentacaoGraos.Tipo.SAIDA:
        resultado = registrar_ajuste(
            usuario=usuario, lote=lote, delta_fisico_kg=-_quantidade_positiva(quantidade_kg),
            chave_idempotencia=chave, **dados,
        )
    else:
        raise SaldoGraosError("Tipo de movimentação inválido.")
    return MovimentacaoGraos.objects.get(pk=resultado.movimentacoes[0].id)


def transferir_graos(**dados):
    resultado = transferir_saldo_fisico(
        usuario=dados["usuario"], lote_origem=dados["lote_origem"],
        lote_destino=dados["lote_destino"], quantidade_kg=dados["quantidade_kg"],
        chave_idempotencia=dados.get("chave_idempotencia"),
        data_movimento=dados.get("data_movimento"),
        observacoes=dados.get("observacoes", ""),
    )
    movimentos = {
        str(item.pk): item
        for item in MovimentacaoGraos.objects.filter(
            pk__in=[movimento.id for movimento in resultado.movimentacoes]
        )
    }
    return tuple(movimentos[item.id] for item in resultado.movimentacoes)


def posicao_graos(queryset=None, *, propriedade=None, armazem=None, cultura="", safra=""):
    filtros = {"armazem": armazem, "cultura": cultura, "safra": safra}
    posicoes = selecionar_posicoes(**filtros)
    if propriedade:
        posicoes = posicoes.filter(armazem__propriedade_id=propriedade)
    return [
        {"posicao_id": item.pk, "cultura": item.cultura, "safra": item.safra,
         "classificacao_codigo": item.classificacao_codigo,
         "armazem_id": item.armazem_id, "armazem": item.armazem.nome,
         "propriedade_id": item.armazem.propriedade_id,
         "propriedade": item.armazem.propriedade.nome,
         "saldo_fisico_kg": item.saldo_fisico_kg,
         "saldo_comprometido_kg": item.saldo_comprometido_kg,
         "saldo_disponivel_kg": item.saldo_disponivel_kg,
         "saldo_kg": item.saldo_fisico_kg, "versao": item.versao}
        for item in posicoes
    ]


def resumo_graos(**filtros):
    posicoes = posicao_graos(**filtros)
    return {"posicoes": len(posicoes), "lotes": len(posicoes),
            "posicoes_com_saldo": sum(item["saldo_fisico_kg"] > 0 for item in posicoes),
            "lotes_com_saldo": sum(item["saldo_fisico_kg"] > 0 for item in posicoes),
            "saldo_total_kg": sum((item["saldo_fisico_kg"] for item in posicoes), ZERO),
            "saldo_comprometido_total_kg": sum((item["saldo_comprometido_kg"] for item in posicoes), ZERO),
            "saldo_disponivel_total_kg": sum((item["saldo_disponivel_kg"] for item in posicoes), ZERO)}

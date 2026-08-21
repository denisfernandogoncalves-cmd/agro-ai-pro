import hashlib
from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.propriedades.models import Propriedade
from apps.talhoes.models import Talhao

from .models import (
    ArmazemGraos,
    CargaColhida,
    GrupoColheita,
    LoteGraos,
    MovimentacaoGraos,
    normalizar_placa,
)
from .services import creditar_producao
from .umidade import (
    UmidadeForaDaTabelaError,
    VERSAO_TABELA_UMIDADE,
    obter_desconto_umidade,
)


MIL = Decimal("0.001")
CEM = Decimal("100")
SESSENTA = Decimal("60")


class CargaColhidaError(ValueError):
    codigo = "carga_colhida_invalida"


class CargaColhidaDuplicadaError(CargaColhidaError):
    codigo = "carga_colhida_duplicada"


def _decimal(valor):
    return Decimal(str(valor)).quantize(MIL, rounding=ROUND_HALF_UP)


def _parcela_desconto(medicao, tolerancia, taxa):
    excesso = max(Decimal("0"), Decimal(str(medicao)) - Decimal(str(tolerancia)))
    desconto = (excesso * Decimal(str(taxa))).quantize(MIL, rounding=ROUND_HALF_UP)
    return excesso, desconto


def calcular_peso_liquido(*, grupo, peso_bruto_kg, umidade_percentual,
                          impureza_percentual, defeitos_percentual, ph=None):
    bruto = _decimal(peso_bruto_kg)
    if bruto <= 0:
        raise CargaColhidaError("O peso bruto deve ser maior que zero.")

    try:
        grupo_cultural, umidade, desconto_umidade = obter_desconto_umidade(
            cultura=grupo.cultura,
            umidade_percentual=umidade_percentual,
        )
    except UmidadeForaDaTabelaError as exc:
        raise CargaColhidaError(str(exc)) from exc

    parcelas = {
        "umidade": {
            "medicao_percentual": str(umidade),
            "grupo_cultural": grupo_cultural,
            "desconto_percentual": str(desconto_umidade),
            "fonte": "tabela_oficial_umidade",
            "versao": VERSAO_TABELA_UMIDADE,
        }
    }
    total_percentual = desconto_umidade
    for nome, medicao, tolerancia, taxa in (
        (
            "impureza",
            impureza_percentual,
            grupo.tolerancia_impureza_percentual,
            grupo.desconto_impureza_por_ponto,
        ),
        (
            "defeitos",
            defeitos_percentual,
            grupo.tolerancia_defeitos_percentual,
            grupo.desconto_defeitos_por_ponto,
        ),
    ):
        excesso, desconto = _parcela_desconto(medicao, tolerancia, taxa)
        total_percentual += desconto
        parcelas[nome] = {
            "medicao_percentual": str(Decimal(str(medicao))),
            "tolerancia_percentual": str(Decimal(str(tolerancia))),
            "excesso_pontos": str(excesso),
            "desconto_por_ponto": str(Decimal(str(taxa))),
            "desconto_percentual": str(desconto),
        }

    ph_minimo = Decimal(str(grupo.ph_minimo))
    taxa_ph = Decimal(str(grupo.desconto_ph_por_ponto))
    if ph in (None, ""):
        if taxa_ph > 0:
            raise CargaColhidaError(
                "Informe o PH para aplicar a regra configurada para este grão."
            )
        ph_medido = None
        deficit_ph = Decimal("0")
    else:
        ph_medido = Decimal(str(ph))
        deficit_ph = max(Decimal("0"), ph_minimo - ph_medido)
    desconto_ph = (deficit_ph * taxa_ph).quantize(MIL, rounding=ROUND_HALF_UP)
    total_percentual += desconto_ph
    parcelas["ph"] = {
        "medicao": None if ph_medido is None else str(ph_medido),
        "minimo": str(ph_minimo),
        "deficit_pontos": str(deficit_ph),
        "desconto_por_ponto": str(taxa_ph),
        "desconto_percentual": str(desconto_ph),
    }

    total_percentual = total_percentual.quantize(MIL, rounding=ROUND_HALF_UP)
    if total_percentual >= CEM:
        raise CargaColhidaError(
            "As regras de desconto resultam em desconto igual ou superior a 100%."
        )
    desconto_kg = (bruto * total_percentual / CEM).quantize(
        MIL,
        rounding=ROUND_HALF_UP,
    )
    liquido = (bruto - desconto_kg).quantize(MIL, rounding=ROUND_HALF_UP)
    sacas = (liquido / SESSENTA).quantize(MIL, rounding=ROUND_HALF_UP)
    regra = {
        "metodo": "tabela_umidade_mais_descontos_classificacao",
        "versao_tabela_umidade": VERSAO_TABELA_UMIDADE,
        "cultura": grupo.cultura,
        "parcelas": parcelas,
        "desconto_total_percentual": str(total_percentual),
        "desconto_total_kg": str(desconto_kg),
    }
    return total_percentual, desconto_kg, liquido, sacas, regra


def _fingerprint(*, grupo_id, data_colheita, placa, motorista, peso_bruto_kg):
    conteudo = "|".join(
        (
            str(grupo_id),
            data_colheita.isoformat(),
            normalizar_placa(placa),
            " ".join(str(motorista or "").strip().upper().split()),
            str(_decimal(peso_bruto_kg)),
        )
    )
    return hashlib.sha256(conteudo.encode("utf-8")).hexdigest()


def _montar_contexto_colheita(*, grupo, propriedades_ids, talhoes_ids):
    propriedades_ids = tuple(dict.fromkeys(
        propriedades_ids or (grupo.propriedade_id,)
    ))
    if grupo.propriedade_id not in propriedades_ids:
        raise CargaColhidaError(
            "A propriedade do grupo deve fazer parte da colheita selecionada."
        )

    propriedades = list(
        Propriedade.objects.filter(pk__in=propriedades_ids)
        .prefetch_related("vinculos_cadpro__cad_pro")
        .order_by("nome", "id")
    )
    if len(propriedades) != len(propriedades_ids):
        raise CargaColhidaError("Uma das propriedades selecionadas não existe.")

    talhoes_ids = tuple(dict.fromkeys(talhoes_ids or ()))
    talhoes = list(
        Talhao.objects.filter(pk__in=talhoes_ids)
        .select_related("propriedade")
        .order_by("propriedade__nome", "nome", "id")
    )
    if len(talhoes) != len(talhoes_ids):
        raise CargaColhidaError("Um dos talhões selecionados não existe.")
    if any(talhao.propriedade_id not in propriedades_ids for talhao in talhoes):
        raise CargaColhidaError(
            "Todos os talhões devem pertencer às propriedades selecionadas."
        )

    area_propriedades = sum(
        (Decimal(str(item.area_hectares)) for item in propriedades),
        Decimal("0"),
    )
    area_talhoes = sum(
        (Decimal(str(item.area_hectares)) for item in talhoes),
        Decimal("0"),
    )
    return {
        "propriedades": [
            {
                "id": item.pk,
                "nome": item.nome,
                "area_hectares": str(item.area_hectares),
                "cad_pro_numeros": [
                    vinculo.cad_pro.codigo
                    for vinculo in item.vinculos_cadpro.all()
                    if vinculo.ativo and vinculo.cad_pro.ativo
                ],
            }
            for item in propriedades
        ],
        "talhoes": [
            {
                "id": item.pk,
                "nome": item.nome,
                "propriedade_id": item.propriedade_id,
                "area_hectares": str(item.area_hectares),
            }
            for item in talhoes
        ],
        "area_total_propriedades_hectares": str(area_propriedades),
        "area_total_talhoes_hectares": str(area_talhoes),
        "grupo_colheita_id": grupo.pk,
        "grupo_colheita_nome": grupo.nome,
        "safra": grupo.safra,
        "cultura": grupo.cultura,
    }


def _obter_lote(grupo, armazem, destinado_semente):
    classificacao = "SEMENTE" if destinado_semente else "PADRAO"
    codigo = f"COLH-{grupo.pk}-{classificacao}"
    lote = LoteGraos.objects.filter(armazem=armazem, codigo=codigo).first()
    if lote:
        if lote.cad_pro_id != grupo.cad_pro_id:
            raise CargaColhidaError("O lote de colheita existente pertence a outro CAD/PRO.")
        return lote
    lote = LoteGraos(
        armazem=armazem,
        cad_pro=grupo.cad_pro,
        codigo=codigo,
        cultura=grupo.cultura,
        safra=grupo.safra,
        classificacao_codigo=classificacao,
        observacoes=f"Lote automático do grupo de colheita {grupo.nome}.",
    )
    lote.full_clean()
    lote.save()
    return lote


@transaction.atomic
def registrar_carga_colhida(*, usuario, grupo_colheita, data_colheita,
                            peso_bruto_kg, umidade_percentual,
                            impureza_percentual, defeitos_percentual, ph=None,
                            destinado_semente=False, local_colheita="", observacoes="",
                            armazem=None, placa="", motorista="",
                            propriedades_selecionadas=(), talhoes_selecionados=()):
    grupo = GrupoColheita.objects.select_for_update().select_related(
        "propriedade",
        "cad_pro",
    ).get(pk=grupo_colheita.pk)
    if armazem is None:
        raise CargaColhidaError("Informe a armazenagem de destino da carga.")
    armazem = ArmazemGraos.objects.select_for_update().select_related(
        "propriedade",
    ).get(pk=armazem.pk)
    if not grupo.ativo:
        raise CargaColhidaError("O grupo de colheita está inativo.")
    if not grupo.cad_pro.ativo:
        raise CargaColhidaError("O CAD/PRO do grupo está inativo.")
    from apps.cadpro.models import CADProPropriedade
    if not CADProPropriedade.objects.filter(
        cad_pro_id=grupo.cad_pro_id,
        propriedade_id=grupo.propriedade_id,
        ativo=True,
    ).exists():
        raise CargaColhidaError(
            "O grupo não possui vínculo CAD/PRO ativo com a propriedade."
        )
    if not armazem.ativo:
        raise CargaColhidaError("O armazém está inativo.")
    if armazem.propriedade_id != grupo.propriedade_id:
        raise CargaColhidaError("O armazém deve pertencer à propriedade do grupo.")
    contexto_colheita = _montar_contexto_colheita(
        grupo=grupo,
        propriedades_ids=propriedades_selecionadas,
        talhoes_ids=talhoes_selecionados,
    )

    placa_normalizada = normalizar_placa(placa)
    motorista_normalizado = " ".join(str(motorista or "").strip().split())
    if placa_normalizada and len(placa_normalizada) != 7:
        raise CargaColhidaError("Informe uma placa brasileira com 7 letras e números.")
    if not placa_normalizada and not motorista_normalizado:
        raise CargaColhidaError(
            "Informe a placa do veículo ou o nome do motorista."
        )
    fingerprint = _fingerprint(
        grupo_id=grupo.pk,
        data_colheita=data_colheita,
        placa=placa_normalizada,
        motorista=motorista_normalizado,
        peso_bruto_kg=peso_bruto_kg,
    )
    if CargaColhida.objects.filter(fingerprint=fingerprint).exists():
        raise CargaColhidaDuplicadaError(
            "Esta carga já foi registrada para o mesmo grupo, data, placa e peso bruto."
        )

    total_percentual, desconto_kg, liquido, sacas, regra = calcular_peso_liquido(
        grupo=grupo,
        peso_bruto_kg=peso_bruto_kg,
        umidade_percentual=umidade_percentual,
        impureza_percentual=impureza_percentual,
        defeitos_percentual=defeitos_percentual,
        ph=ph,
    )
    lote = _obter_lote(grupo, armazem, destinado_semente)
    resultado = creditar_producao(
        usuario=usuario,
        lote=lote,
        quantidade_kg=liquido,
        chave_idempotencia=f"carga-colhida:{fingerprint}",
        data_movimento=data_colheita,
        referencia_externa=f"CARGA-{fingerprint[:12]}",
        observacoes=observacoes,
        metadados={
            "origem": "registro_manual_carga_colhida",
            "grupo_colheita_id": grupo.pk,
            "placa": placa_normalizada,
            "peso_bruto_kg": str(_decimal(peso_bruto_kg)),
            "regra_desconto": regra,
        },
    )
    movimento = MovimentacaoGraos.objects.get(pk=resultado.movimentacoes[0].id)
    carga = CargaColhida(
        grupo_colheita=grupo,
        armazem=armazem,
        lote=lote,
        data_colheita=data_colheita,
        placa=placa_normalizada,
        motorista=motorista_normalizado,
        peso_bruto_kg=_decimal(peso_bruto_kg),
        umidade_percentual=umidade_percentual,
        impureza_percentual=impureza_percentual,
        defeitos_percentual=defeitos_percentual,
        ph=ph,
        destinado_semente=destinado_semente,
        local_colheita=" ".join(str(local_colheita or "").strip().split()),
        desconto_total_percentual=total_percentual,
        desconto_total_kg=desconto_kg,
        peso_liquido_kg=liquido,
        sacas_60kg=sacas,
        regra_desconto_aplicada=regra,
        contexto_colheita=contexto_colheita,
        fingerprint=fingerprint,
        movimentacao=movimento,
        observacoes=observacoes or "",
        criado_por=usuario,
    )
    try:
        carga.full_clean()
        carga.save()
    except IntegrityError as exc:
        raise CargaColhidaDuplicadaError(
            "Esta carga já foi registrada para o mesmo grupo, data, placa e peso bruto."
        ) from exc
    except ValidationError as exc:
        raise CargaColhidaError(str(exc)) from exc
    return carga

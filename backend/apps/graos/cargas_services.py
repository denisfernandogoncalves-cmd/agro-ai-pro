import hashlib
from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.cadpro.models import CADPro, CADProPropriedade
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
from .services import (
    bloquear_cadpro_para_saldo,
    creditar_producao,
    estornar_movimentacao,
)
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


class CargaColhidaSubstituidaError(CargaColhidaError):
    codigo = "carga_colhida_substituida"

    def __init__(self, *, substituida_por_id):
        self.substituida_por_id = substituida_por_id
        super().__init__(
            "Esta carga já foi substituída. Cancele ou edite a versão ativa mais recente."
        )


def _decimal(valor):
    return Decimal(str(valor)).quantize(MIL, rounding=ROUND_HALF_UP)


def _parcela_desconto(medicao, tolerancia, taxa):
    excesso = max(Decimal("0"), Decimal(str(medicao)) - Decimal(str(tolerancia)))
    desconto = (excesso * Decimal(str(taxa))).quantize(MIL, rounding=ROUND_HALF_UP)
    return excesso, desconto


def calcular_peso_liquido(
    *,
    peso_bruto_kg,
    umidade_percentual,
    impureza_percentual,
    defeitos_percentual,
    ph=None,
    cultura="",
    grupo=None,
    tolerancia_impureza_percentual=None,
    desconto_impureza_por_ponto=None,
    tolerancia_defeitos_percentual=None,
    desconto_defeitos_por_ponto=None,
    ph_minimo=None,
    desconto_ph_por_ponto=None,
):
    bruto = _decimal(peso_bruto_kg)
    if bruto <= 0:
        raise CargaColhidaError("O peso bruto deve ser maior que zero.")

    if grupo is not None:
        cultura = grupo.cultura
        tolerancia_impureza_percentual = (
            grupo.tolerancia_impureza_percentual
            if tolerancia_impureza_percentual is None
            else tolerancia_impureza_percentual
        )
        desconto_impureza_por_ponto = (
            grupo.desconto_impureza_por_ponto
            if desconto_impureza_por_ponto is None
            else desconto_impureza_por_ponto
        )
        tolerancia_defeitos_percentual = (
            grupo.tolerancia_defeitos_percentual
            if tolerancia_defeitos_percentual is None
            else tolerancia_defeitos_percentual
        )
        desconto_defeitos_por_ponto = (
            grupo.desconto_defeitos_por_ponto
            if desconto_defeitos_por_ponto is None
            else desconto_defeitos_por_ponto
        )
        ph_minimo = grupo.ph_minimo if ph_minimo is None else ph_minimo
        desconto_ph_por_ponto = (
            grupo.desconto_ph_por_ponto
            if desconto_ph_por_ponto is None
            else desconto_ph_por_ponto
        )

    cultura = " ".join(str(cultura or "").strip().split()).title()
    tolerancia_impureza_percentual = (
        Decimal("100.00")
        if tolerancia_impureza_percentual is None
        else Decimal(str(tolerancia_impureza_percentual))
    )
    desconto_impureza_por_ponto = (
        Decimal("0.000")
        if desconto_impureza_por_ponto is None
        else Decimal(str(desconto_impureza_por_ponto))
    )
    tolerancia_defeitos_percentual = (
        Decimal("100.00")
        if tolerancia_defeitos_percentual is None
        else Decimal(str(tolerancia_defeitos_percentual))
    )
    desconto_defeitos_por_ponto = (
        Decimal("0.000")
        if desconto_defeitos_por_ponto is None
        else Decimal(str(desconto_defeitos_por_ponto))
    )
    ph_minimo = Decimal("0.00") if ph_minimo is None else Decimal(str(ph_minimo))
    desconto_ph_por_ponto = (
        Decimal("0.000")
        if desconto_ph_por_ponto is None
        else Decimal(str(desconto_ph_por_ponto))
    )

    try:
        grupo_cultural, umidade, desconto_umidade = obter_desconto_umidade(
            cultura=cultura,
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
            tolerancia_impureza_percentual,
            desconto_impureza_por_ponto,
        ),
        (
            "defeitos",
            defeitos_percentual,
            tolerancia_defeitos_percentual,
            desconto_defeitos_por_ponto,
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

    taxa_ph = desconto_ph_por_ponto
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
        "cultura": cultura,
        "origem_regras_classificacao": (
            "grupo_colheita_legado" if grupo is not None else "parametros_da_carga"
        ),
        "parcelas": parcelas,
        "desconto_total_percentual": str(total_percentual),
        "desconto_total_kg": str(desconto_kg),
    }
    return total_percentual, desconto_kg, liquido, sacas, regra


def _fingerprint(
    *,
    propriedade_id,
    cad_pro_id,
    cultura,
    safra,
    armazem_id,
    data_colheita,
    placa,
    motorista,
    peso_bruto_kg,
    correcao_de_id=None,
    chave_registro="",
):
    chave_registro = " ".join(str(chave_registro or "").strip().split())
    if chave_registro:
        conteudo = f"CHAVE-REGISTRO|{chave_registro}"
        return hashlib.sha256(conteudo.encode("utf-8")).hexdigest()
    conteudo = "|".join(
        (
            str(propriedade_id),
            str(cad_pro_id),
            str(cultura).strip().upper(),
            str(safra).strip().upper(),
            str(armazem_id),
            data_colheita.isoformat(),
            normalizar_placa(placa),
            " ".join(str(motorista or "").strip().upper().split()),
            str(_decimal(peso_bruto_kg)),
            f"CORRECAO:{correcao_de_id}" if correcao_de_id else "ORIGINAL",
        )
    )
    return hashlib.sha256(conteudo.encode("utf-8")).hexdigest()


def _montar_contexto_colheita(
    *, propriedade, cad_pro, propriedades_ids, talhoes_ids, grupo=None
):
    cad_pro_principal = cad_pro
    propriedades_ids = tuple(dict.fromkeys(
        propriedades_ids or (propriedade.pk,)
    ))
    if propriedade.pk not in propriedades_ids:
        raise CargaColhidaError(
            "A propriedade principal deve fazer parte da colheita selecionada."
        )
    if grupo is None and propriedades_ids != (propriedade.pk,):
        raise CargaColhidaError(
            "O fluxo direto aceita uma propriedade por carga. Registre cargas "
            "separadas para manter o saldo oficial de cada CAD/PRO."
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
    propriedades_contexto = []
    for item in propriedades:
        cadpros = [
            vinculo.cad_pro
            for vinculo in item.vinculos_cadpro.all()
            if vinculo.ativo and vinculo.cad_pro.ativo
        ]
        if item.pk == propriedade.pk:
            cad_pro_item = next(
                (cad for cad in cadpros if cad.pk == cad_pro_principal.pk),
                None,
            )
        elif len(cadpros) == 1:
            cad_pro_item = cadpros[0]
        else:
            cad_pro_item = None
        if cad_pro_item is None:
            if not cadpros:
                raise CargaColhidaError(
                    f"A propriedade {item.nome} não possui CAD/PRO ativo."
                )
            raise CargaColhidaError(
                f"A propriedade {item.nome} possui mais de um CAD/PRO ativo. "
                "Mantenha um único CAD/PRO ativo para realizar o rateio."
            )
        propriedades_contexto.append(
            {
                "id": item.pk,
                "nome": item.nome,
                "proprietario": item.proprietario,
                "area_hectares": str(item.area_hectares),
                "cad_pro_id": str(cad_pro_item.pk),
                "cad_pro_numero": cad_pro_item.codigo,
                "cad_pro_numeros": [cad.codigo for cad in cadpros],
            }
        )
    contexto = {
        "propriedades": propriedades_contexto,
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
        "propriedade_principal_id": propriedade.pk,
        "cad_pro_id": str(cad_pro_principal.pk),
    }
    if grupo is not None:
        contexto["grupo_colheita_legado_id"] = grupo.pk
        contexto["grupo_colheita_legado_nome"] = grupo.nome
    return contexto


def _aplicar_rateio_producao(contexto, *, peso_liquido_kg, sacas_60kg):
    propriedades = contexto["propriedades"]
    area_total = sum(
        (Decimal(item["area_hectares"]) for item in propriedades),
        Decimal("0"),
    )
    if area_total <= 0:
        raise CargaColhidaError(
            "A soma das áreas das propriedades deve ser maior que zero."
        )

    liquido_total = _decimal(peso_liquido_kg)
    sacas_total = _decimal(sacas_60kg)
    media = (sacas_total / area_total).quantize(MIL, rounding=ROUND_HALF_UP)
    restante_kg = liquido_total
    restante_sacas = sacas_total
    rateio = []
    for indice, item in enumerate(propriedades):
        area = Decimal(item["area_hectares"])
        proporcao = area / area_total
        ultimo = indice == len(propriedades) - 1
        peso_rateado = restante_kg if ultimo else (
            liquido_total * proporcao
        ).quantize(MIL, rounding=ROUND_HALF_UP)
        sacas_rateadas = restante_sacas if ultimo else (
            sacas_total * proporcao
        ).quantize(MIL, rounding=ROUND_HALF_UP)
        restante_kg -= peso_rateado
        restante_sacas -= sacas_rateadas
        rateio.append(
            {
                "propriedade_id": item["id"],
                "propriedade_nome": item["nome"],
                "proprietario": item["proprietario"],
                "cad_pro_id": item["cad_pro_id"],
                "cad_pro_numero": item["cad_pro_numero"],
                "area_hectares": str(area),
                "proporcao": str(
                    proporcao.quantize(Decimal("0.000000001"), rounding=ROUND_HALF_UP)
                ),
                "peso_liquido_kg": str(peso_rateado),
                "sacas_60kg": str(sacas_rateadas),
                "media_sacas_hectare": str(media),
            }
        )
    contexto["rateio_producao"] = rateio
    contexto["regra_rateio_producao"] = {
        "metodo": "proporcional_area_declarada",
        "versao": "2026-08-20",
        "area_total_hectares": str(area_total),
        "peso_liquido_total_kg": str(liquido_total),
        "sacas_60kg_total": str(sacas_total),
        "media_sacas_hectare": str(media),
        "sem_duplicacao": True,
    }
    return contexto


def _obter_lote(
    *, cad_pro, cultura, safra, armazem, destinado_semente, grupo=None
):
    classificacao = "SEMENTE" if destinado_semente else "PADRAO"
    if grupo is None:
        lote = (
            LoteGraos.objects.filter(
                armazem=armazem,
                cad_pro=cad_pro,
                cultura__iexact=cultura,
                safra=safra,
                classificacao_codigo=classificacao,
                ativo=True,
            )
            .order_by("id")
            .first()
        )
        semente_codigo = "|".join(
            (str(cad_pro.pk), str(armazem.pk), cultura.upper(), safra.upper(), classificacao)
        )
        codigo = (
            f"COLH-{hashlib.sha256(semente_codigo.encode('utf-8')).hexdigest()[:12].upper()}"
            f"-{classificacao}"
        )
        observacoes = "Lote automático de cargas colhidas sem grupo."
    else:
        codigo = f"COLH-{grupo.pk}-{classificacao}"
        lote = (
            LoteGraos.objects.filter(armazem=armazem, codigo=codigo)
            .first()
        )
        observacoes = f"Lote automático do grupo de colheita legado {grupo.nome}."

    if lote:
        dimensoes = (
            lote.cad_pro_id == cad_pro.pk,
            lote.cultura.casefold() == cultura.casefold(),
            lote.safra == safra,
            lote.classificacao_codigo == classificacao,
        )
        if not all(dimensoes):
            raise CargaColhidaError(
                "O lote automático existente não corresponde ao CAD/PRO, cultura, "
                "safra e classificação da carga."
            )
        return lote

    lote = LoteGraos(
        armazem=armazem,
        cad_pro=cad_pro,
        codigo=codigo,
        cultura=cultura,
        safra=safra,
        classificacao_codigo=classificacao,
        observacoes=observacoes,
    )
    try:
        with transaction.atomic():
            lote.full_clean()
            lote.save()
    except IntegrityError:
        lote = LoteGraos.objects.get(armazem=armazem, codigo=codigo)
        dimensoes = (
            lote.cad_pro_id == cad_pro.pk,
            lote.cultura.casefold() == cultura.casefold(),
            lote.safra == safra,
            lote.classificacao_codigo == classificacao,
        )
        if not all(dimensoes):
            raise CargaColhidaError(
                "O lote automático criado em concorrência não corresponde ao "
                "contexto da carga."
            )
    return lote


def _resolver_contexto_principal(*, propriedade, cad_pro, grupo_colheita):
    grupo = None
    if grupo_colheita is not None:
        grupo = (
            GrupoColheita.objects.select_for_update()
            .select_related("propriedade", "cad_pro")
            .get(pk=grupo_colheita.pk)
        )
        if not grupo.ativo:
            raise CargaColhidaError("O grupo de colheita legado está inativo.")
        propriedade = grupo.propriedade
        cad_pro = grupo.cad_pro
    if propriedade is None:
        raise CargaColhidaError("Informe a propriedade da carga.")
    if cad_pro is None:
        raise CargaColhidaError("Informe o CAD/PRO da carga.")
    propriedade = Propriedade.objects.get(pk=propriedade.pk)
    cad_pro = CADPro.objects.get(pk=cad_pro.pk)
    if not cad_pro.ativo:
        raise CargaColhidaError("O CAD/PRO da carga está inativo.")
    if not CADProPropriedade.objects.filter(
        cad_pro=cad_pro,
        propriedade=propriedade,
        ativo=True,
    ).exists():
        raise CargaColhidaError(
            "O CAD/PRO deve possuir vínculo ativo com a propriedade da carga."
        )
    return propriedade, cad_pro, grupo


@transaction.atomic
def registrar_carga_colhida(
    *,
    usuario,
    data_colheita,
    peso_bruto_kg,
    umidade_percentual,
    impureza_percentual,
    defeitos_percentual,
    propriedade=None,
    cad_pro=None,
    cultura="",
    safra="",
    armazem=None,
    ph=None,
    destinado_semente=False,
    local_colheita="",
    observacoes="",
    placa="",
    motorista="",
    talhoes_selecionados=(),
    tolerancia_impureza_percentual=None,
    desconto_impureza_por_ponto=None,
    tolerancia_defeitos_percentual=None,
    desconto_defeitos_por_ponto=None,
    ph_minimo=None,
    desconto_ph_por_ponto=None,
    grupo_colheita=None,
    propriedades_selecionadas=(),
    correcao_de_id=None,
    chave_registro="",
):
    propriedade, cad_pro, grupo = _resolver_contexto_principal(
        propriedade=propriedade,
        cad_pro=cad_pro,
        grupo_colheita=grupo_colheita,
    )
    if grupo is not None:
        cultura = grupo.cultura
        safra = grupo.safra
    cultura = " ".join(str(cultura or "").strip().split()).title()
    safra = " ".join(str(safra or "").strip().split())
    if not cultura:
        raise CargaColhidaError("Informe a cultura da carga.")
    if not safra:
        raise CargaColhidaError("Informe a safra da carga.")
    if armazem is None:
        raise CargaColhidaError("Informe a armazenagem de destino da carga.")
    armazem = ArmazemGraos.objects.select_related("propriedade").get(pk=armazem.pk)
    if not armazem.ativo:
        raise CargaColhidaError("A armazenagem está inativa.")
    if armazem.propriedade_id != propriedade.pk:
        raise CargaColhidaError("A armazenagem deve pertencer à propriedade da carga.")

    contexto_colheita = _montar_contexto_colheita(
        propriedade=propriedade,
        cad_pro=cad_pro,
        grupo=grupo,
        propriedades_ids=propriedades_selecionadas,
        talhoes_ids=talhoes_selecionados,
    )
    contexto_colheita.update(cultura=cultura, safra=safra)

    placa_normalizada = normalizar_placa(placa)
    motorista_normalizado = " ".join(str(motorista or "").strip().split())
    if placa_normalizada and len(placa_normalizada) != 7:
        raise CargaColhidaError("Informe uma placa brasileira com 7 letras e números.")
    if not placa_normalizada and not motorista_normalizado:
        raise CargaColhidaError("Informe a placa do veículo ou o nome do motorista.")

    fingerprint = _fingerprint(
        propriedade_id=propriedade.pk,
        cad_pro_id=cad_pro.pk,
        cultura=cultura,
        safra=safra,
        armazem_id=armazem.pk,
        data_colheita=data_colheita,
        placa=placa_normalizada,
        motorista=motorista_normalizado,
        peso_bruto_kg=peso_bruto_kg,
        correcao_de_id=correcao_de_id,
        chave_registro=chave_registro,
    )
    if CargaColhida.objects.filter(fingerprint=fingerprint).exists():
        raise CargaColhidaDuplicadaError(
            "Esta carga já foi registrada para o mesmo contexto, data, veículo e peso bruto."
        )

    total_percentual, desconto_kg, liquido, sacas, regra = calcular_peso_liquido(
        grupo=grupo,
        cultura=cultura,
        peso_bruto_kg=peso_bruto_kg,
        umidade_percentual=umidade_percentual,
        impureza_percentual=impureza_percentual,
        defeitos_percentual=defeitos_percentual,
        ph=ph,
        tolerancia_impureza_percentual=tolerancia_impureza_percentual,
        desconto_impureza_por_ponto=desconto_impureza_por_ponto,
        tolerancia_defeitos_percentual=tolerancia_defeitos_percentual,
        desconto_defeitos_por_ponto=desconto_defeitos_por_ponto,
        ph_minimo=ph_minimo,
        desconto_ph_por_ponto=desconto_ph_por_ponto,
    )
    contexto_colheita = _aplicar_rateio_producao(
        contexto_colheita,
        peso_liquido_kg=liquido,
        sacas_60kg=sacas,
    )
    if chave_registro:
        contexto_colheita["chave_registro"] = " ".join(
            str(chave_registro).strip().split()
        )
    lote = _obter_lote(
        cad_pro=cad_pro,
        cultura=cultura,
        safra=safra,
        armazem=armazem,
        destinado_semente=destinado_semente,
        grupo=grupo,
    )
    metadados = {
        "origem": "registro_manual_carga_colhida",
        "propriedade_id": propriedade.pk,
        "cad_pro_id": str(cad_pro.pk),
        "cultura": cultura,
        "safra": safra,
        "placa": placa_normalizada,
        "peso_bruto_kg": str(_decimal(peso_bruto_kg)),
        "regra_desconto": regra,
    }
    if grupo is not None:
        metadados["grupo_colheita_legado_id"] = grupo.pk
    if correcao_de_id:
        metadados["correcao_de_carga_id"] = correcao_de_id
    resultado = creditar_producao(
        usuario=usuario,
        lote=lote,
        quantidade_kg=liquido,
        chave_idempotencia=f"carga-colhida:{fingerprint}",
        data_movimento=data_colheita,
        referencia_externa=f"CARGA-{fingerprint[:12]}",
        observacoes=observacoes,
        metadados=metadados,
    )
    movimento = MovimentacaoGraos.objects.get(pk=resultado.movimentacoes[0].id)
    carga = CargaColhida(
        grupo_colheita=grupo,
        propriedade=propriedade,
        cad_pro=cad_pro,
        cultura=cultura,
        safra=safra,
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
            "Esta carga já foi registrada para o mesmo contexto, data, veículo e peso bruto."
        ) from exc
    except ValidationError as exc:
        raise CargaColhidaError(str(exc)) from exc
    return carga


@transaction.atomic
def cancelar_carga_colhida(*, usuario, carga, motivo="Exclusão solicitada pelo usuário."):
    carga_id = getattr(carga, "pk", carga)
    carga = CargaColhida.objects.select_for_update().get(pk=carga_id)
    if carga.status == CargaColhida.Status.CANCELADA:
        return carga
    if carga.status == CargaColhida.Status.SUBSTITUIDA:
        raise CargaColhidaSubstituidaError(
            substituida_por_id=carga.substituida_por_id
        )
    estorno_existente = (
        MovimentacaoGraos.objects.filter(estorno_de_id=carga.movimentacao_id)
        .order_by("criado_em", "id")
        .first()
    )
    if estorno_existente is None:
        estornar_movimentacao(
            usuario=usuario,
            movimentacao=carga.movimentacao,
            chave_idempotencia=f"carga-colhida:cancelar:{carga.pk}",
            data_movimento=timezone.localdate(),
            referencia_externa=f"CARGA-CANCELADA-{carga.pk}",
            observacoes=motivo,
            metadados={"carga_colhida_id": carga.pk, "operacao": "cancelamento"},
            permitir_carga_colhida=True,
        )
        cancelada_em = timezone.now()
        cancelada_por = usuario
    else:
        cancelada_em = estorno_existente.criado_em
        cancelada_por = estorno_existente.criado_por
    carga._registrar_encerramento(
        status=CargaColhida.Status.CANCELADA,
        cancelada_em=cancelada_em,
        cancelada_por=cancelada_por,
        motivo=motivo,
    )
    return carga


@transaction.atomic
def corrigir_carga_colhida(*, usuario, carga, motivo="Correção solicitada pelo usuário.", **dados):
    carga_id = getattr(carga, "pk", carga)
    original = CargaColhida.objects.select_for_update().get(pk=carga_id)
    if original.status != CargaColhida.Status.ATIVA:
        raise CargaColhidaError(
            "Esta carga já foi encerrada. Edite a versão ativa mais recente."
        )
    if MovimentacaoGraos.objects.filter(estorno_de_id=original.movimentacao_id).exists():
        raise CargaColhidaError(
            "A carga já possui estorno e não pode ser editada. Atualize a listagem."
        )
    destino_cad_pro = dados.get("cad_pro")
    destino_grupo = dados.get("grupo_colheita")
    destino_cad_pro_id = (
        getattr(destino_cad_pro, "pk", None)
        or getattr(destino_grupo, "cad_pro_id", None)
        or original.cad_pro_id
    )
    for cad_pro_id in sorted(
        {original.cad_pro_id, destino_cad_pro_id},
        key=str,
    ):
        bloquear_cadpro_para_saldo(cad_pro_id)
    estornar_movimentacao(
        usuario=usuario,
        movimentacao=original.movimentacao,
        chave_idempotencia=f"carga-colhida:retificar:{original.pk}",
        data_movimento=timezone.localdate(),
        referencia_externa=f"CARGA-RETIFICADA-{original.pk}",
        observacoes=motivo,
        metadados={"carga_colhida_id": original.pk, "operacao": "retificacao"},
        permitir_carga_colhida=True,
    )
    substituta = registrar_carga_colhida(
        usuario=usuario,
        correcao_de_id=original.pk,
        **dados,
    )
    original._registrar_encerramento(
        status=CargaColhida.Status.SUBSTITUIDA,
        cancelada_em=timezone.now(),
        cancelada_por=usuario,
        motivo=motivo,
        substituida_por=substituta,
    )
    return substituta

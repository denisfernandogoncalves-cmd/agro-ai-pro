import hashlib
from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from .models import (
    ArmazemGraos,
    CargaColhida,
    GrupoColheita,
    LoteGraos,
    MovimentacaoGraos,
    normalizar_placa,
)
from .services import creditar_producao


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
                          impureza_percentual, defeitos_percentual):
    bruto = _decimal(peso_bruto_kg)
    if bruto <= 0:
        raise CargaColhidaError("O peso bruto deve ser maior que zero.")

    parcelas = {}
    total_percentual = Decimal("0")
    for nome, medicao, tolerancia, taxa in (
        (
            "umidade",
            umidade_percentual,
            grupo.tolerancia_umidade_percentual,
            grupo.desconto_umidade_por_ponto,
        ),
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
        "metodo": "excesso_de_pontos_x_desconto_por_ponto",
        "parcelas": parcelas,
        "desconto_total_percentual": str(total_percentual),
        "desconto_total_kg": str(desconto_kg),
    }
    return total_percentual, desconto_kg, liquido, sacas, regra


def _fingerprint(*, grupo_id, data_colheita, placa, peso_bruto_kg):
    conteudo = "|".join(
        (
            str(grupo_id),
            data_colheita.isoformat(),
            normalizar_placa(placa),
            str(_decimal(peso_bruto_kg)),
        )
    )
    return hashlib.sha256(conteudo.encode("utf-8")).hexdigest()


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
def registrar_carga_colhida(*, usuario, grupo_colheita, armazem=None, data_colheita,
                            placa, peso_bruto_kg, umidade_percentual,
                            impureza_percentual, defeitos_percentual, ph=None,
                            destinado_semente=False, local_colheita="", observacoes=""):
    grupo = GrupoColheita.objects.select_for_update().select_related(
        "propriedade",
        "cad_pro",
    ).get(pk=grupo_colheita.pk)
    armazem = armazem or grupo.armazem_padrao
    if armazem is None:
        raise CargaColhidaError("O grupo não possui armazenagem padrão configurada.")
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

    placa_normalizada = normalizar_placa(placa)
    if len(placa_normalizada) != 7:
        raise CargaColhidaError("Informe uma placa brasileira com 7 letras e números.")
    fingerprint = _fingerprint(
        grupo_id=grupo.pk,
        data_colheita=data_colheita,
        placa=placa_normalizada,
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

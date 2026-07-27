from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Avg, Count, Sum

from .grain_services import ProducaoError
from .joint_models import LoteConjuntoProducao, ParticipanteLoteConjunto


KG = Decimal("0.001")
AREA = Decimal("0.0001")
PERCENTUAL = Decimal("0.00001")


def quantizar(valor, casas=KG):
    return Decimal(str(valor or 0)).quantize(casas, rounding=ROUND_HALF_UP)


def recalcular_lote(lote):
    participantes = lote.participantes.all()
    cargas = lote.cargas.all()
    areas = participantes.aggregate(
        cadastrada=Sum("area_cadastrada_ha"),
        colhida=Sum("area_colhida_ha"),
    )
    totais = cargas.aggregate(
        bruto=Sum("peso_bruto_kg"),
        tara=Sum("tara_kg"),
        liquido=Sum("peso_liquido_kg"),
        umidade=Avg("umidade_percentual"),
        impureza=Avg("impureza_percentual"),
        defeitos=Avg("defeitos_percentual"),
    )
    lote.area_total_cadastrada_ha = quantizar(areas["cadastrada"], AREA)
    lote.area_total_colhida_ha = quantizar(areas["colhida"], AREA)
    lote.peso_bruto_total_kg = quantizar(totais["bruto"])
    lote.tara_total_kg = quantizar(totais["tara"])
    lote.peso_liquido_total_kg = quantizar(totais["liquido"])
    lote.umidade_media = quantizar(totais["umidade"], Decimal("0.001"))
    lote.impureza_media = quantizar(totais["impureza"], Decimal("0.001"))
    lote.defeitos_medios = quantizar(totais["defeitos"], Decimal("0.001"))
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
    total_area = lote.area_total_colhida_ha
    acumulado = Decimal("0")
    lista = list(participantes.order_by("id"))
    for indice, participante in enumerate(lista):
        if total_area <= 0:
            percentual = Decimal("0")
        elif indice == len(lista) - 1:
            percentual = Decimal("100") - acumulado
        else:
            percentual = quantizar(
                participante.area_colhida_ha / total_area * Decimal("100"),
                PERCENTUAL,
            )
            acumulado += percentual
        participante.percentual_area = percentual
        participante.save(update_fields=("percentual_area", "atualizado_em"))
    return lote


def validar_lote_para_confirmacao(lote):
    participantes = list(lote.participantes.select_related("propriedade", "cadpro"))
    if len(participantes) < 2:
        raise ProducaoError("O lote conjunto exige pelo menos duas propriedades participantes.")
    if lote.cargas.count() < 1:
        raise ProducaoError("Inclua ao menos uma carga antes de confirmar o lote.")
    if lote.area_total_colhida_ha <= 0:
        raise ProducaoError("A área efetivamente colhida deve ser maior que zero.")
    if lote.peso_liquido_total_kg <= 0:
        raise ProducaoError("O total líquido das cargas deve ser maior que zero.")
    for participante in participantes:
        participante.full_clean()
    if lote.modo_rateio != LoteConjuntoProducao.ModoRateio.SEM_RATEIO:
        sem_cadpro = [item.propriedade.nome for item in participantes if not item.cadpro_id]
        if sem_cadpro:
            raise ProducaoError(
                "O rateio exige CAD/PRO confiável para cada propriedade: "
                + ", ".join(sem_cadpro)
            )
    return participantes


def rateio_por_area(lote, participantes):
    total = lote.peso_liquido_total_kg
    acumulado = Decimal("0")
    distribuicoes = []
    for indice, participante in enumerate(participantes):
        if indice == len(participantes) - 1:
            quantidade = total - acumulado
        else:
            quantidade = quantizar(
                total * participante.area_colhida_ha / lote.area_total_colhida_ha
            )
            acumulado += quantidade
        distribuicoes.append(
            {"participante": participante, "cadpro": participante.cadpro, "quantidade_kg": quantidade}
        )
    return distribuicoes


def rateio_manual(lote, participantes):
    distribuicoes = []
    total = Decimal("0")
    for participante in participantes:
        if participante.quantidade_rateada_kg is None:
            raise ProducaoError("Informe a quantidade manual de todas as propriedades.")
        quantidade = quantizar(participante.quantidade_rateada_kg)
        total += quantidade
        distribuicoes.append(
            {"participante": participante, "cadpro": participante.cadpro, "quantidade_kg": quantidade}
        )
    if quantizar(total) != quantizar(lote.peso_liquido_total_kg):
        raise ProducaoError(
            f"O rateio manual soma {total} kg, mas o lote possui {lote.peso_liquido_total_kg} kg."
        )
    return distribuicoes


def resumo_lote(lote):
    cargas = lote.cargas.all()
    saldo_conjunto = lote.saldos_conjuntos.aggregate(total=Sum("quantidade_kg"))["total"] or Decimal("0")
    distribuido = lote.cadpros_participantes.aggregate(total=Sum("quantidade_atribuida_kg"))["total"] or Decimal("0")
    por_motorista = list(
        cargas.values("motorista_id", "motorista__nome")
        .annotate(quantidade_kg=Sum("peso_liquido_kg"), viagens=Count("id"))
        .order_by("motorista__nome")
    )
    por_placa = list(
        cargas.values("placa_cavalo_informada")
        .annotate(quantidade_kg=Sum("peso_liquido_kg"), viagens=Count("id"))
        .order_by("placa_cavalo_informada")
    )
    quantidade_cargas = cargas.count()
    return {
        "codigo": lote.codigo,
        "propriedades": lote.participantes.count(),
        "cargas": quantidade_cargas,
        "area_total_cadastrada_ha": lote.area_total_cadastrada_ha,
        "area_total_colhida_ha": lote.area_total_colhida_ha,
        "quantidade_kg": lote.peso_liquido_total_kg,
        "quantidade_toneladas": lote.quantidade_toneladas,
        "quantidade_sacas": lote.quantidade_sacas,
        "produtividade_kg_ha": lote.produtividade_kg_ha,
        "produtividade_sacas_ha": lote.produtividade_sacas_ha,
        "saldo_conjunto_kg": saldo_conjunto,
        "distribuido_kg": distribuido,
        "peso_medio_carga_kg": quantizar(lote.peso_liquido_total_kg / quantidade_cargas) if quantidade_cargas else Decimal("0"),
        "por_motorista": por_motorista,
        "por_placa": por_placa,
    }

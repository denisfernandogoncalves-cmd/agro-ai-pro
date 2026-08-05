from collections import defaultdict
from decimal import Decimal

from apps.graos.models import ArmazemGraos
from apps.graos.services import posicao_graos


LIMITE_OCUPACAO_ATENCAO = Decimal("90")


def adicionar_insights_graos(*, adicionar, propriedade=None, safra=""):
    posicoes = posicao_graos(propriedade=propriedade, safra=safra)
    posicoes_com_saldo = [item for item in posicoes if item["saldo_kg"] > 0]
    saldo_total = sum(
        (item["saldo_kg"] for item in posicoes_com_saldo),
        Decimal("0"),
    )

    if saldo_total > 0:
        adicionar(
            "graos_saldo_disponivel",
            "informativo",
            "Estoque de grãos disponível",
            (
                f"Há {saldo_total:.3f} kg distribuídos em "
                f"{len(posicoes_com_saldo)} lote(s) com saldo"
                f"{f' na safra {safra}' if safra else ''}."
            ),
            (
                "Conferir o estoque físico e os compromissos comerciais antes "
                "de planejar novas saídas."
            ),
            "graos",
        )

    lotes_inativos = [
        item for item in posicoes_com_saldo if not item["ativo"]
    ]
    if lotes_inativos:
        saldo_inativo = sum(
            (item["saldo_kg"] for item in lotes_inativos),
            Decimal("0"),
        )
        adicionar(
            "graos_lotes_inativos_com_saldo",
            "atencao",
            "Lotes inativos ainda possuem saldo",
            (
                f"{len(lotes_inativos)} lote(s) inativo(s) concentram "
                f"{saldo_inativo:.3f} kg."
            ),
            (
                "Revisar a situação dos lotes e confirmar a destinação do saldo "
                "antes de encerrar o controle operacional."
            ),
            "graos",
        )

    posicoes_capacidade = (
        posicao_graos(propriedade=propriedade) if safra else posicoes
    )

    posicoes_inconsistentes = [
        item for item in posicoes_capacidade if item["saldo_kg"] < 0
    ]
    if posicoes_inconsistentes:
        deficit_total = sum(
            (-item["saldo_kg"] for item in posicoes_inconsistentes),
            Decimal("0"),
        )
        adicionar(
            "graos_saldos_inconsistentes",
            "critico",
            "Ledger de grãos possui saldos inconsistentes",
            (
                f"{len(posicoes_inconsistentes)} lote(s) apresentam saldo negativo, "
                f"com déficit total de {deficit_total:.3f} kg. Esses déficits não "
                "foram usados para reduzir a ocupação dos armazéns."
            ),
            (
                "Revisar as movimentações do ledger e conferir o estoque físico "
                "antes de registrar novas operações nos lotes afetados."
            ),
            "graos",
        )

    saldos_por_armazem = defaultdict(lambda: Decimal("0"))
    for item in posicoes_capacidade:
        saldos_por_armazem[item["armazem_id"]] += max(
            item["saldo_kg"],
            Decimal("0"),
        )

    armazens = ArmazemGraos.objects.filter(ativo=True)
    if propriedade:
        armazens = armazens.filter(propriedade_id=propriedade)
    for armazem in armazens.select_related("propriedade"):
        saldo = saldos_por_armazem[armazem.id]
        ocupacao = saldo / armazem.capacidade_kg * Decimal("100")
        if ocupacao < LIMITE_OCUPACAO_ATENCAO:
            continue
        disponivel = max(armazem.capacidade_kg - saldo, Decimal("0"))
        adicionar(
            f"graos_ocupacao_armazem_{armazem.id}",
            "atencao",
            f"Armazém {armazem.nome} próximo da capacidade",
            (
                f"Ocupação de {ocupacao:.2f}% ({saldo:.3f} de "
                f"{armazem.capacidade_kg:.3f} kg); capacidade disponível: "
                f"{disponivel:.3f} kg."
            ),
            (
                "Planejar expedição ou capacidade alternativa antes de novas "
                "entradas."
            ),
            "graos",
        )

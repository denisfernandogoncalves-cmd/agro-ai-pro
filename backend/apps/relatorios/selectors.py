from decimal import Decimal
from math import ceil

from django.utils import timezone

from apps.cadpro.selectors import selecionar_cadpros
from apps.graos.models import ArmazemGraos, MovimentacaoGraos
from apps.graos.selectors import (
    selecionar_movimentacoes_saldo,
    selecionar_posicoes,
    selecionar_reservas,
)
from apps.vendas.selectors import selecionar_vendas


ZERO = Decimal("0.000")


def _texto_decimal(valor):
    return str((valor or ZERO).quantize(Decimal("0.001")))


def _pagina(itens, numero, tamanho):
    total = len(itens)
    inicio = (numero - 1) * tamanho
    return {
        "pagina": numero,
        "por_pagina": tamanho,
        "total": total,
        "total_paginas": ceil(total / tamanho) if total else 0,
        "resultados": itens[inicio : inicio + tamanho],
    }


def _filtrar_posicoes(filtros):
    return selecionar_posicoes(
        cad_pro=filtros.get("cad_pro"),
        propriedade=filtros.get("propriedade"),
        cultura=filtros.get("cultura", ""),
        safra=filtros.get("safra", ""),
        classificacao_codigo=filtros.get("classificacao_codigo", ""),
        armazem=filtros.get("armazem"),
    ).order_by(
        "cad_pro__codigo_normalizado",
        "cultura",
        "safra",
        "classificacao_codigo",
        "armazem__nome",
        "pk",
    )


def _ids_posicoes(posicoes):
    return [item.pk for item in posicoes]


def _periodo(queryset, campo, filtros):
    if filtros.get("data_inicio"):
        queryset = queryset.filter(**{f"{campo}__gte": filtros["data_inicio"]})
    if filtros.get("data_fim"):
        queryset = queryset.filter(**{f"{campo}__lte": filtros["data_fim"]})
    return queryset


def _item_posicao(item):
    return {
        "id": item.pk,
        "cad_pro": str(item.cad_pro_id),
        "cad_pro_codigo": item.cad_pro.codigo,
        "cad_pro_descricao": item.cad_pro.descricao,
        "propriedade": item.armazem.propriedade_id,
        "propriedade_nome": item.armazem.propriedade.nome,
        "cultura": item.cultura,
        "safra": item.safra,
        "classificacao_codigo": item.classificacao_codigo,
        "armazem": item.armazem_id,
        "armazem_nome": item.armazem.nome,
        "saldo_fisico_kg": _texto_decimal(item.saldo_fisico_kg),
        "saldo_comprometido_kg": _texto_decimal(item.saldo_comprometido_kg),
        "saldo_disponivel_kg": _texto_decimal(
            item.saldo_fisico_kg - item.saldo_comprometido_kg
        ),
        "atualizado_em": item.atualizado_em,
    }


def _totais_posicoes(posicoes):
    fisico = sum((item.saldo_fisico_kg for item in posicoes), ZERO)
    comprometido = sum((item.saldo_comprometido_kg for item in posicoes), ZERO)
    return {
        "posicoes": len(posicoes),
        "saldo_fisico_kg": _texto_decimal(fisico),
        "saldo_comprometido_kg": _texto_decimal(comprometido),
        "saldo_disponivel_kg": _texto_decimal(fisico - comprometido),
    }


def _subtotais(posicoes, chave, rotulo):
    grupos = {}
    for item in posicoes:
        identidade, nome = chave(item)
        grupo = grupos.setdefault(
            str(identidade),
            {rotulo: identidade, f"{rotulo}_nome": nome, "_posicoes": []},
        )
        grupo["_posicoes"].append(item)
    resultado = []
    for grupo in grupos.values():
        itens = grupo.pop("_posicoes")
        resultado.append({**grupo, **_totais_posicoes(itens)})
    return resultado


def _movimentos(filtros, posicao_ids):
    queryset = selecionar_movimentacoes_saldo().filter(posicao_id__in=posicao_ids)
    return _periodo(queryset, "data_movimento", filtros).order_by(
        "-data_movimento", "-id"
    )


def _item_movimento(item):
    carga = getattr(item, "carga_colhida", None)
    return {
        "id": item.pk,
        "operacao": item.operacao,
        "tipo": item.tipo,
        "data": item.data_movimento,
        "quantidade_kg": _texto_decimal(item.quantidade_kg),
        "delta_fisico_kg": _texto_decimal(item.delta_fisico_kg),
        "delta_comprometido_kg": _texto_decimal(item.delta_comprometido_kg),
        "lote_operacional": item.lote_id,
        "lote_operacional_codigo": item.lote.codigo,
        "origem": item.origem_id,
        "origem_tipo": item.origem.tipo,
        "referencia_externa": item.referencia_externa,
        "posicao": _item_posicao(item.posicao),
        "snapshot_anterior": item.snapshot_anterior,
        "snapshot_posterior": item.snapshot_posterior,
        "carga_colhida": carga.pk if carga else None,
        "grupo_colheita": carga.grupo_colheita_id if carga else None,
        "grupo_colheita_nome": carga.grupo_colheita.nome if carga else "",
        "placa_carga": carga.placa if carga else "",
    }


def _reservas(filtros, posicao_ids):
    queryset = selecionar_reservas().filter(posicao_id__in=posicao_ids)
    queryset = _periodo(queryset, "criado_em__date", filtros)
    return queryset.order_by("-criado_em", "-id")


def _item_reserva(item):
    return {
        "id": item.pk,
        "status": item.status,
        "quantidade_kg": _texto_decimal(item.quantidade_kg),
        "saldo_reservado_kg": _texto_decimal(item.saldo_reservado_kg),
        "referencia_externa": item.referencia_externa,
        "criado_em": item.criado_em,
        "posicao": _item_posicao(item.posicao),
    }


def _vendas(filtros, posicao_ids):
    queryset = selecionar_vendas().filter(posicao_id__in=posicao_ids)
    return _periodo(queryset, "data_contrato", filtros).order_by(
        "-data_contrato", "-id"
    )


def _item_venda(item):
    return {
        "id": item.pk,
        "numero_contrato": item.numero_contrato,
        "cliente_nome": item.cliente_nome,
        "status": item.status,
        "data_contrato": item.data_contrato,
        "quantidade_kg": _texto_decimal(item.quantidade_kg),
        "quantidade_reservada_kg": _texto_decimal(item.quantidade_reservada_kg),
        "quantidade_entregue_kg": _texto_decimal(item.quantidade_entregue_kg),
        "quantidade_devolvida_kg": _texto_decimal(item.quantidade_devolvida_kg),
        "quantidade_aberta_kg": _texto_decimal(item.quantidade_aberta_kg),
        "posicao": _item_posicao(item.posicao),
        "lote_operacional_codigo": item.lote.codigo,
        "origem_fisica_alocada": False,
    }


def _entregas(vendas, filtros):
    itens = []
    inicio, fim = filtros.get("data_inicio"), filtros.get("data_fim")
    for venda in vendas:
        for entrega in venda.entregas.all():
            if inicio and entrega.data_entrega < inicio:
                continue
            if fim and entrega.data_entrega > fim:
                continue
            itens.append(
                {
                    "id": entrega.pk,
                    "venda": venda.pk,
                    "numero_contrato": venda.numero_contrato,
                    "cliente_nome": venda.cliente_nome,
                    "data": entrega.data_entrega,
                    "quantidade_kg": _texto_decimal(entrega.quantidade_kg),
                    "movimentacao": entrega.movimentacao_id,
                    "posicao": _item_posicao(venda.posicao),
                }
            )
    return sorted(itens, key=lambda item: (item["data"], item["id"]), reverse=True)


def _producoes(movimentos):
    return [
        _item_movimento(item)
        for item in movimentos
        if item.operacao == MovimentacaoGraos.Operacao.CREDITO_PRODUCAO
    ]


def _rastreabilidade(movimentos):
    return [_item_movimento(item) for item in movimentos]


def selecionar_relatorio_operacional(**filtros):
    secao = filtros["secao"]
    pagina, por_pagina = filtros["pagina"], filtros["por_pagina"]
    posicoes = list(_filtrar_posicoes(filtros))
    ids = _ids_posicoes(posicoes)
    movimentos = list(_movimentos(filtros, ids))
    reservas = list(_reservas(filtros, ids))
    vendas = list(_vendas(filtros, ids))

    secoes = {
        "saldos": [_item_posicao(item) for item in posicoes],
        "producao": _producoes(movimentos),
        "reservas": [_item_reserva(item) for item in reservas],
        "vendas": [_item_venda(item) for item in vendas],
        "entregas": _entregas(vendas, filtros),
        "movimentacoes": [_item_movimento(item) for item in movimentos],
        "rastreabilidade": _rastreabilidade(movimentos),
    }
    producao_total = sum(
        (item.quantidade_kg for item in movimentos if item.operacao == MovimentacaoGraos.Operacao.CREDITO_PRODUCAO),
        ZERO,
    )
    reserva_aberta = sum((item.saldo_reservado_kg for item in reservas), ZERO)
    venda_total = sum((item.quantidade_kg for item in vendas), ZERO)
    entrega_total = sum(
        (Decimal(item["quantidade_kg"]) for item in secoes["entregas"]), ZERO
    )
    return {
        "gerado_em": timezone.now(),
        "filtros": {
            chave: str(valor) if valor is not None else ""
            for chave, valor in filtros.items()
            if chave not in {"pagina", "por_pagina"}
        },
        "totais": {
            **_totais_posicoes(posicoes),
            "producao_kg": _texto_decimal(producao_total),
            "reservas_abertas_kg": _texto_decimal(reserva_aberta),
            "vendas_kg": _texto_decimal(venda_total),
            "entregas_kg": _texto_decimal(entrega_total),
        },
        "por_cad_pro": _subtotais(
            posicoes,
            lambda item: (str(item.cad_pro_id), item.cad_pro.codigo),
            "cad_pro",
        ),
        "por_propriedade": _subtotais(
            posicoes,
            lambda item: (item.armazem.propriedade_id, item.armazem.propriedade.nome),
            "propriedade",
        ),
        "secao": secao,
        "dados": _pagina(secoes[secao], pagina, por_pagina),
    }


def selecionar_opcoes_relatorio():
    posicoes = selecionar_posicoes()
    return {
        "cadpros": list(
            selecionar_cadpros().values("id", "codigo", "descricao").order_by("codigo_normalizado")
        ),
        "culturas": list(posicoes.values_list("cultura", flat=True).distinct().order_by("cultura")),
        "safras": list(posicoes.values_list("safra", flat=True).distinct().order_by("safra")),
        "classificacoes": list(
            posicoes.values_list("classificacao_codigo", flat=True).distinct().order_by("classificacao_codigo")
        ),
        "armazens": list(
            ArmazemGraos.objects.select_related("propriedade")
            .values("id", "nome", "propriedade_id", "propriedade__nome")
            .order_by("nome", "id")
        ),
    }

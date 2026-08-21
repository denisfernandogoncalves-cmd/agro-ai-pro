from decimal import Decimal, ROUND_HALF_UP
from math import ceil

from django.utils import timezone

from apps.cadpro.models import CADPro, normalizar_codigo_cadpro
from apps.cadpro.selectors import selecionar_cadpros
from apps.graos.models import ArmazemGraos, CargaColhida, MovimentacaoGraos
from apps.graos.selectors import (
    selecionar_movimentacoes_saldo,
    selecionar_posicoes,
    selecionar_reservas,
)
from apps.vendas.selectors import selecionar_entregas, selecionar_vendas
from apps.propriedades.models import Propriedade


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
    queryset = selecionar_posicoes(
        cad_pro=filtros.get("cad_pro"),
        propriedade=filtros.get("propriedade"),
        cultura=filtros.get("cultura", ""),
        safra=filtros.get("safra", ""),
        classificacao_codigo=filtros.get("classificacao_codigo", ""),
        armazem=filtros.get("armazem"),
    )
    if filtros.get("proprietario"):
        queryset = queryset.filter(
            armazem__propriedade__proprietario__iexact=filtros["proprietario"]
        )
    return queryset.order_by(
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
    if filtros.get("numero_contrato"):
        queryset = queryset.filter(
            numero_contrato__icontains=filtros["numero_contrato"]
        )
    if filtros.get("comprador"):
        queryset = queryset.filter(cliente_nome__icontains=filtros["comprador"])
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


def _entregas(filtros, posicao_ids):
    queryset = selecionar_entregas().filter(venda__posicao_id__in=posicao_ids)
    if filtros.get("numero_contrato"):
        queryset = queryset.filter(
            venda__numero_contrato__icontains=filtros["numero_contrato"]
        )
    if filtros.get("comprador"):
        queryset = queryset.filter(
            venda__cliente_nome__icontains=filtros["comprador"]
        )
    return _periodo(queryset, "data_entrega", filtros).order_by(
        "-data_entrega", "-id"
    )


def _item_entrega(item):
    return {
        "id": item.pk,
        "venda": item.venda_id,
        "numero_contrato": item.venda.numero_contrato,
        "cliente_nome": item.venda.cliente_nome,
        "data": item.data_entrega,
        "quantidade_kg": _texto_decimal(item.quantidade_kg),
        "destino": item.destino or item.venda.cliente_nome,
        "placa": item.placa,
        "nota_produtor": item.nota_produtor,
        "nota_empresa": item.nota_empresa,
        "movimentacao": item.movimentacao_id,
        "posicao": _item_posicao(item.venda.posicao),
    }


def _producoes(movimentos):
    return [
        _item_movimento(item)
        for item in movimentos
        if item.operacao == MovimentacaoGraos.Operacao.CREDITO_PRODUCAO
    ]


def _rastreabilidade(movimentos):
    return [_item_movimento(item) for item in movimentos]


def _cargas_do_periodo(filtros):
    queryset = CargaColhida.objects.select_related(
        "grupo_colheita",
        "grupo_colheita__propriedade",
        "grupo_colheita__cad_pro",
        "armazem",
    )
    queryset = _periodo(queryset, "data_colheita", filtros)
    if filtros.get("cultura"):
        queryset = queryset.filter(
            grupo_colheita__cultura__iexact=filtros["cultura"]
        )
    if filtros.get("safra"):
        queryset = queryset.filter(grupo_colheita__safra=filtros["safra"])
    if filtros.get("classificacao_codigo"):
        semente = filtros["classificacao_codigo"] == "SEMENTE"
        queryset = queryset.filter(destinado_semente=semente)
    if filtros.get("armazem"):
        queryset = queryset.filter(armazem_id=filtros["armazem"])
    if "destinado_semente" in filtros:
        queryset = queryset.filter(
            destinado_semente=filtros["destinado_semente"]
        )
    if filtros.get("motorista"):
        queryset = queryset.filter(motorista__icontains=filtros["motorista"])
    if filtros.get("placa"):
        queryset = queryset.filter(placa__icontains=filtros["placa"])
    return queryset.order_by("-data_colheita", "-id")


def _rateios_da_carga(carga):
    contexto = carga.contexto_colheita or {}
    rateios = contexto.get("rateio_producao")
    if isinstance(rateios, list) and rateios:
        return rateios
    propriedades = contexto.get("propriedades")
    if isinstance(propriedades, list) and propriedades:
        area_total = sum(
            (Decimal(str(item.get("area_hectares", "0"))) for item in propriedades),
            ZERO,
        )
        if area_total > 0:
            proprietarios = dict(
                Propriedade.objects.filter(
                    pk__in=[item.get("id") for item in propriedades]
                ).values_list("pk", "proprietario")
            )
            restante_kg = carga.peso_liquido_kg
            restante_sacas = carga.sacas_60kg
            reconstruidos = []
            for indice, item in enumerate(propriedades):
                area = Decimal(str(item["area_hectares"]))
                proporcao = area / area_total
                ultimo = indice == len(propriedades) - 1
                peso = restante_kg if ultimo else (
                    carga.peso_liquido_kg * proporcao
                ).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
                sacas = restante_sacas if ultimo else (
                    carga.sacas_60kg * proporcao
                ).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
                restante_kg -= peso
                restante_sacas -= sacas
                codigos = item.get("cad_pro_numeros") or []
                codigo = codigos[0] if len(codigos) == 1 else carga.grupo_colheita.cad_pro.codigo
                cad_pro = CADPro.objects.filter(
                    codigo_normalizado=normalizar_codigo_cadpro(codigo)
                ).first()
                reconstruidos.append({
                    "propriedade_id": item["id"],
                    "propriedade_nome": item["nome"],
                    "proprietario": proprietarios.get(int(item["id"]), ""),
                    "cad_pro_id": str(cad_pro.pk if cad_pro else carga.grupo_colheita.cad_pro_id),
                    "cad_pro_numero": codigo,
                    "area_hectares": str(area),
                    "proporcao": str(proporcao.quantize(
                        Decimal("0.000000001"), rounding=ROUND_HALF_UP
                    )),
                    "peso_liquido_kg": str(peso),
                    "sacas_60kg": str(sacas),
                    "media_sacas_hectare": _texto_decimal(carga.sacas_60kg / area_total),
                })
            return reconstruidos
    return [{
        "propriedade_id": carga.grupo_colheita.propriedade_id,
        "propriedade_nome": carga.grupo_colheita.propriedade.nome,
        "proprietario": carga.grupo_colheita.propriedade.proprietario,
        "cad_pro_id": str(carga.grupo_colheita.cad_pro_id),
        "cad_pro_numero": carga.grupo_colheita.cad_pro.codigo,
        "area_hectares": str(carga.grupo_colheita.propriedade.area_hectares),
        "proporcao": "1.000000000",
        "peso_liquido_kg": str(carga.peso_liquido_kg),
        "sacas_60kg": str(carga.sacas_60kg),
        "media_sacas_hectare": _texto_decimal(
            carga.sacas_60kg / carga.grupo_colheita.propriedade.area_hectares
        ),
    }]


def _rateio_corresponde(rateio, filtros):
    propriedade = filtros.get("propriedade")
    cad_pro = filtros.get("cad_pro")
    proprietario = filtros.get("proprietario", "").strip().casefold()
    return (
        (not propriedade or int(rateio["propriedade_id"]) == propriedade)
        and (not cad_pro or str(rateio["cad_pro_id"]) == str(cad_pro))
        and (
            not proprietario
            or str(rateio.get("proprietario", "")).strip().casefold() == proprietario
        )
    )


def _item_produtividade(carga, rateio):
    peso = Decimal(rateio["peso_liquido_kg"])
    sacas = Decimal(rateio["sacas_60kg"])
    return {
        "id": carga.pk * 1000000 + int(rateio["propriedade_id"]),
        "carga_colhida": carga.pk,
        "data": carga.data_colheita,
        "propriedade": int(rateio["propriedade_id"]),
        "propriedade_nome": rateio["propriedade_nome"],
        "proprietario": rateio.get("proprietario", ""),
        "cad_pro": rateio["cad_pro_id"],
        "cad_pro_codigo": rateio["cad_pro_numero"],
        "cultura": carga.grupo_colheita.cultura,
        "safra": carga.grupo_colheita.safra,
        "area_hectares": _texto_decimal(Decimal(rateio["area_hectares"])),
        "proporcao": rateio["proporcao"],
        "quantidade_kg": _texto_decimal(peso),
        "sacas_60kg": _texto_decimal(sacas),
        "media_sacas_hectare": rateio["media_sacas_hectare"],
        "destinado_semente": carga.destinado_semente,
        "semente_kg": _texto_decimal(peso if carga.destinado_semente else ZERO),
        "semente_sacas_60kg": _texto_decimal(
            sacas if carga.destinado_semente else ZERO
        ),
        "armazem": carga.armazem_id,
        "armazem_nome": carga.armazem.nome,
        "placa": carga.placa,
        "motorista": carga.motorista,
    }


def _produtividade(filtros):
    itens = []
    for carga in _cargas_do_periodo(filtros):
        for rateio in _rateios_da_carga(carga):
            if _rateio_corresponde(rateio, filtros):
                itens.append(_item_produtividade(carga, rateio))
    return itens


def _motoristas(filtros):
    grupos = {}
    for carga in _cargas_do_periodo(filtros):
        rateios = [
            item for item in _rateios_da_carga(carga)
            if _rateio_corresponde(item, filtros)
        ]
        if not rateios:
            continue
        peso = sum((Decimal(item["peso_liquido_kg"]) for item in rateios), ZERO)
        sacas = sum((Decimal(item["sacas_60kg"]) for item in rateios), ZERO)
        nome = carga.motorista or "Motorista não informado"
        chave = " ".join(nome.casefold().split())
        grupo = grupos.setdefault(chave, {
            "motorista": nome,
            "peso_liquido_kg": ZERO,
            "sacas_60kg": ZERO,
            "semente_kg": ZERO,
            "cargas_ids": set(),
            "placas": set(),
            "armazens": set(),
        })
        grupo["peso_liquido_kg"] += peso
        grupo["sacas_60kg"] += sacas
        if carga.destinado_semente:
            grupo["semente_kg"] += peso
        grupo["cargas_ids"].add(carga.pk)
        if carga.placa:
            grupo["placas"].add(carga.placa)
        grupo["armazens"].add(carga.armazem.nome)
    return [
        {
            "id": indice,
            "motorista": item["motorista"],
            "quantidade_cargas": len(item["cargas_ids"]),
            "quantidade_kg": _texto_decimal(item["peso_liquido_kg"]),
            "sacas_60kg": _texto_decimal(item["sacas_60kg"]),
            "semente_kg": _texto_decimal(item["semente_kg"]),
            "placas": sorted(item["placas"]),
            "armazens": sorted(item["armazens"]),
        }
        for indice, item in enumerate(
            sorted(grupos.values(), key=lambda item: item["motorista"].casefold()),
            start=1,
        )
    ]


def _produtividade_por_cad_pro(itens):
    grupos = {}
    for item in itens:
        grupo = grupos.setdefault(item["cad_pro"], {
            "cad_pro": item["cad_pro"],
            "cad_pro_nome": item["cad_pro_codigo"],
            "producao_kg": ZERO,
            "producao_sacas_60kg": ZERO,
            "semente_kg": ZERO,
            "areas": {},
        })
        grupo["producao_kg"] += Decimal(item["quantidade_kg"])
        grupo["producao_sacas_60kg"] += Decimal(item["sacas_60kg"])
        grupo["semente_kg"] += Decimal(item["semente_kg"])
        chave_area = (item["propriedade"], item["cultura"], item["safra"])
        grupo["areas"].setdefault(chave_area, Decimal(item["area_hectares"]))
    resultado = []
    for grupo in grupos.values():
        area = sum(grupo.pop("areas").values(), ZERO)
        media = grupo["producao_sacas_60kg"] / area if area else ZERO
        resultado.append({
            **grupo,
            "producao_kg": _texto_decimal(grupo["producao_kg"]),
            "producao_sacas_60kg": _texto_decimal(grupo["producao_sacas_60kg"]),
            "semente_kg": _texto_decimal(grupo["semente_kg"]),
            "area_hectares": _texto_decimal(area),
            "media_sacas_hectare": _texto_decimal(media),
        })
    return resultado


def selecionar_relatorio_operacional(**filtros):
    secao = filtros["secao"]
    pagina, por_pagina = filtros["pagina"], filtros["por_pagina"]
    posicoes = list(_filtrar_posicoes(filtros))
    ids = _ids_posicoes(posicoes)
    movimentos = list(_movimentos(filtros, ids))
    reservas = list(_reservas(filtros, ids))
    vendas = list(_vendas(filtros, ids))
    entregas = list(_entregas(filtros, ids))
    produtividade = _produtividade(filtros)
    motoristas = _motoristas(filtros)

    secoes = {
        "saldos": [_item_posicao(item) for item in posicoes],
        "producao": _producoes(movimentos),
        "reservas": [_item_reserva(item) for item in reservas],
        "vendas": [_item_venda(item) for item in vendas],
        "entregas": [_item_entrega(item) for item in entregas],
        "movimentacoes": [_item_movimento(item) for item in movimentos],
        "rastreabilidade": _rastreabilidade(movimentos),
        "produtividade": produtividade,
        "motoristas": motoristas,
    }
    producao_total = sum(
        (item.quantidade_kg for item in movimentos if item.operacao == MovimentacaoGraos.Operacao.CREDITO_PRODUCAO),
        ZERO,
    )
    reserva_aberta = sum((item.saldo_reservado_kg for item in reservas), ZERO)
    venda_total = sum((item.quantidade_kg for item in vendas), ZERO)
    entrega_total = sum((item.quantidade_kg for item in entregas), ZERO)
    producao_rateada = sum(
        (Decimal(item["quantidade_kg"]) for item in produtividade), ZERO
    )
    semente_rateada = sum(
        (Decimal(item["semente_kg"]) for item in produtividade), ZERO
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
            "producao_rateada_kg": _texto_decimal(producao_rateada),
            "semente_kg": _texto_decimal(semente_rateada),
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
        "produtividade_por_cad_pro": _produtividade_por_cad_pro(produtividade),
        "secao": secao,
        "dados": _pagina(secoes[secao], pagina, por_pagina),
    }


def selecionar_opcoes_relatorio():
    posicoes = selecionar_posicoes()
    vendas = selecionar_vendas()
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
        "proprietarios": list(
            ArmazemGraos.objects.exclude(propriedade__proprietario="")
            .values_list("propriedade__proprietario", flat=True)
            .distinct()
            .order_by("propriedade__proprietario")
        ),
        "compradores": list(
            vendas.values_list("cliente_nome", flat=True)
            .distinct()
            .order_by("cliente_nome")
        ),
        "contratos": list(
            vendas.values_list("numero_contrato", flat=True)
            .distinct()
            .order_by("numero_contrato")
        ),
        "motoristas": list(
            CargaColhida.objects.exclude(motorista="")
            .values_list("motorista", flat=True)
            .distinct()
            .order_by("motorista")
        ),
        "placas": list(
            CargaColhida.objects.exclude(placa="")
            .values_list("placa", flat=True)
            .distinct()
            .order_by("placa")
        ),
    }

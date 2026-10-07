"""Classificação histórica reconstruída pelos snapshots imutáveis de edição."""
from decimal import Decimal
from .models import MovimentoProducaoTerceiro


def eventos_terceiros(armazem, movimentos=None):
    if movimentos is None:
        movimentos = list(MovimentoProducaoTerceiro.objects.filter(entrada__armazem=armazem)
                          .select_related('entrada').order_by('entrada_id', 'id'))
    iniciais = {}
    for m in movimentos:
        snapshot = m.snapshot_antes if m.tipo == 'edicao' else m.snapshot_depois
        if snapshot and m.entrada_id not in iniciais:
            iniciais[m.entrada_id] = snapshot
    estados = {}
    for m in movimentos:
        estado = estados.setdefault(m.entrada_id, iniciais.get(m.entrada_id, {
            'cultura':m.entrada.cultura, 'safra':m.entrada.safra,
            'peso_liquido_kg':str(m.entrada.peso_liquido_kg)}))
        novo = m.snapshot_depois if m.tipo == 'edicao' else None
        if novo and (estado['cultura'].casefold(), estado['safra'].casefold()) != (novo['cultura'].casefold(), novo['safra'].casefold()):
            yield m.pk, m.data_movimento, estado['cultura'], estado['safra'], -Decimal(estado['peso_liquido_kg'])
            yield m.pk, m.data_movimento, novo['cultura'], novo['safra'], Decimal(novo['peso_liquido_kg'])
        else:
            yield m.pk, m.data_movimento, estado['cultura'], estado['safra'], m.delta_kg
        if novo:
            estados[m.entrada_id] = novo


def periodo_terceiros(armazem, cultura, safra, fim):
    return sorted([(pk, data, delta) for pk, data, c, s, delta in eventos_terceiros(armazem)
            if data <= fim and c.strip().casefold() == cultura.strip().casefold()
            and s.strip().casefold() == safra.strip().casefold()],key=lambda v:v[0])

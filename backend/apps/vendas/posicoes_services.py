"""Cria somente o contexto de estoque, sem inventar uma entrada de produção."""
import hashlib
import json

from django.db import transaction

from apps.graos.models import LoteGraos
from apps.graos.services import (
    _bloquear_armazens, _bloquear_cadpros_ativos_para_saldo,
    _bloquear_posicao_lote, _validar_estado_lote,
)


@transaction.atomic
def resolver_posicao_inicial(dados):
    _bloquear_cadpros_ativos_para_saldo((dados["cad_pro"].pk,))
    _bloquear_armazens((dados["armazem"].pk,))
    dimensoes = {
        "propriedade": dados["propriedade"], "cad_pro": dados["cad_pro"],
        "cultura": dados["cultura"], "safra": dados["safra"].strip(),
        "classificacao_codigo": dados["classificacao_codigo"].strip().upper(),
        "armazem": dados["armazem"],
    }
    lote = LoteGraos.objects.filter(**dimensoes, ativo=True).order_by("pk").first()
    if not lote:
        chave = json.dumps({k: str(getattr(v, "pk", v)) for k, v in dimensoes.items()}, sort_keys=True)
        codigo = "VENDA-" + hashlib.sha256(chave.encode()).hexdigest()[:32]
        lote = LoteGraos(codigo=codigo, **dimensoes)
        _validar_estado_lote(lote)
        lote.save()
    else:
        _validar_estado_lote(lote)
    return _bloquear_posicao_lote(lote)

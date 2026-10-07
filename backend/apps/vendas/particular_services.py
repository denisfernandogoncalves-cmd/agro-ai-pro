"""Venda particular rateada por área, com snapshot e baixa atômica no ledger."""
import hashlib
import json
from decimal import Decimal, ROUND_DOWN

from django.db import transaction

from apps.cadpro.models import CADProPropriedade
from apps.graos.models import PosicaoSaldoGraos
from apps.graos.services import _bloquear_armazens, _bloquear_cadpros_ativos_para_saldo
from apps.propriedades.models import Propriedade
from .models import RateioVendaParticular
from .posicoes_services import resolver_posicao_inicial
from .services import (
    VendaGraosConflitoError, VendaGraosError, _chave, _quantidade,
    _validar_repeticao, registrar_venda_com_saida,
)


def _canonico(valor):
    if isinstance(valor, dict):
        return {k: _canonico(v) for k, v in valor.items()}
    if isinstance(valor, list):
        return [_canonico(v) for v in valor]
    if hasattr(valor, "pk"):
        return str(valor.pk)
    if valor is None or isinstance(valor, (str, int, bool)):
        return valor
    return str(valor)


def _digest(valor):
    return hashlib.sha256(json.dumps(_canonico(valor), sort_keys=True).encode()).hexdigest()


def previa_particular(*, contexto, quantidade_kg):
    quantidade = _quantidade(quantidade_kg)
    propriedades = list(Propriedade.objects.order_by("pk"))
    if not propriedades:
        raise VendaGraosError("Cadastre as propriedades antes de registrar a venda PARTICULAR.")
    vinculos = list(CADProPropriedade.objects.filter(
        ativo=True, cad_pro__ativo=True,
    ).select_related("cad_pro").order_by("propriedade_id", "cad_pro_id"))
    parcelas = []
    for propriedade in propriedades:
        candidatos = [v.cad_pro for v in vinculos if v.propriedade_id == propriedade.pk]
        if len(candidatos) != 1:
            raise VendaGraosError(
                f"{propriedade.nome}: o rateio precisa de um único CAD/PRO ativo vinculado. "
                "Revise os vínculos desta propriedade."
            )
        if propriedade.area_hectares <= 0:
            raise VendaGraosError(f"Informe uma área maior que zero para {propriedade.nome}.")
        parcelas.append({
            "propriedade": propriedade.pk, "propriedade_nome": propriedade.nome,
            "cad_pro": str(candidatos[0].pk), "cad_pro_codigo": candidatos[0].codigo,
            "area_hectares": str(propriedade.area_hectares),
        })
    area_total = sum(Decimal(p["area_hectares"]) for p in parcelas)
    # Maiores restos: precisão de 1 grama, soma exata e nenhuma parcela negativa.
    exatos = [quantidade * Decimal(p["area_hectares"]) / area_total for p in parcelas]
    pesos = [valor.quantize(Decimal("0.001"), rounding=ROUND_DOWN) for valor in exatos]
    restantes = int((quantidade - sum(pesos)) / Decimal("0.001"))
    ordem = sorted(range(len(parcelas)), key=lambda i: (-(exatos[i] - pesos[i]), parcelas[i]["propriedade"]))
    for indice in ordem[:restantes]:
        pesos[indice] += Decimal("0.001")
    for parcela, peso in zip(parcelas, pesos):
        parcela["quantidade_kg"] = str(peso)
        posicao = PosicaoSaldoGraos.objects.filter(propriedade_id=parcela["propriedade"],cad_pro_id=parcela["cad_pro"],cultura=contexto["cultura"],safra=contexto["safra"].strip(),classificacao_codigo=contexto["classificacao_codigo"].strip().upper(),armazem=contexto["armazem"]).first()
        anterior = posicao.saldo_fisico_kg if posicao else Decimal("0")
        parcela["saldo_anterior_kg"] = str(anterior)
        parcela["saldo_posterior_kg"] = str(anterior-peso)
    snapshot = {
        "metodo": "proporcional_area_hectares", "contexto": _canonico(contexto),
        "area_total_hectares": str(area_total), "quantidade_total_kg": str(quantidade),
        "parcelas": parcelas,
    }
    return {**snapshot, "hash_previa": _digest(snapshot)}


@transaction.atomic
def registrar_particular(*, usuario, chave_idempotencia, dados):
    chave = _chave(chave_idempotencia)
    hash_requisicao = _digest(dados)
    grupo, _ = RateioVendaParticular.objects.get_or_create(
        chave_idempotencia=chave,
        defaults={"hash_requisicao": hash_requisicao, "criado_por": usuario},
    )
    grupo = RateioVendaParticular.objects.select_for_update().get(pk=grupo.pk)
    _validar_repeticao(grupo.hash_requisicao, hash_requisicao)
    if grupo.snapshot:
        return grupo.parcelas.order_by("pk").first()
    contexto = dados["contexto_particular"]
    ids_cadpro = CADProPropriedade.objects.filter(ativo=True, cad_pro__ativo=True).values_list("cad_pro_id", flat=True)
    _bloquear_cadpros_ativos_para_saldo(set(ids_cadpro))
    _bloquear_armazens((contexto["armazem"].pk,))
    list(Propriedade.objects.select_for_update().order_by("pk"))
    snapshot = previa_particular(contexto=contexto, quantidade_kg=dados["quantidade_kg"])
    if dados.get("hash_previa") != snapshot["hash_previa"]:
        raise VendaGraosConflitoError("O rateio mudou. Confira a prévia atualizada e registre novamente.")
    tara_distribuida = Decimal("0")
    parcelas_positivas = [p for p in snapshot["parcelas"] if Decimal(p["quantidade_kg"]) > 0]
    for parcela in snapshot["parcelas"]:
        if Decimal(parcela["quantidade_kg"]) == 0:
            continue
        vinculo = CADProPropriedade.objects.select_related("propriedade", "cad_pro").get(
            propriedade_id=parcela["propriedade"], cad_pro_id=parcela["cad_pro"], ativo=True,
        )
        posicao = resolver_posicao_inicial({
            **contexto, "propriedade": vinculo.propriedade, "cad_pro": vinculo.cad_pro,
        })
        campos = {k: v for k, v in dados.items() if k not in (
            "contexto_particular", "hash_previa", "posicao", "nova_posicao",
        )}
        campos.update(posicao=posicao, quantidade_kg=parcela["quantidade_kg"])
        if dados.get("peso_bruto_kg") is not None:
            tara = (dados["tara_kg"] * Decimal(parcela["quantidade_kg"]) / dados["quantidade_kg"]).quantize(Decimal("0.001"), rounding=ROUND_DOWN)
            if parcela is parcelas_positivas[-1]:
                tara = dados["tara_kg"] - tara_distribuida
            tara_distribuida += tara
            campos.update(tara_kg=tara, peso_bruto_kg=Decimal(parcela["quantidade_kg"]) + tara)
        venda = registrar_venda_com_saida(
            usuario=usuario, chave_idempotencia=f"particular:{grupo.pk}:{vinculo.propriedade_id}", dados=campos,
        )
        venda.rateio_particular = grupo
        venda.save(update_fields=("rateio_particular",))
        parcela["venda_id"] = venda.pk
    grupo.snapshot = snapshot
    grupo.save(update_fields=("snapshot",))
    return grupo.parcelas.order_by("pk").first()

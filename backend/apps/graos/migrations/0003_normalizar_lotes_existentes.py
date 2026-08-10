import hashlib
from decimal import Decimal

from django.db import migrations


def normalizar(apps, schema_editor):
    Lote = apps.get_model("graos", "LoteGraos")
    Movimento = apps.get_model("graos", "MovimentacaoGraos")
    Origem = apps.get_model("graos", "OrigemSaldoGraos")
    Posicao = apps.get_model("graos", "PosicaoSaldoGraos")
    Vinculo = apps.get_model("cadpro", "CADProPropriedade")

    for lote in Lote.objects.select_related("armazem").all().iterator():
        classificacao = str(lote.classificacao_codigo or "PADRAO").strip().upper()
        atualizacoes = {"classificacao_codigo": classificacao or "PADRAO"}
        if not lote.cad_pro_id:
            vinculos = list(
                Vinculo.objects.filter(
                    propriedade_id=lote.armazem.propriedade_id,
                    ativo=True,
                    cad_pro__ativo=True,
                ).values_list("cad_pro_id", flat=True)[:2]
            )
            if len(vinculos) == 1:
                atualizacoes["cad_pro_id"] = vinculos[0]
        Lote.objects.filter(pk=lote.pk).update(**atualizacoes)

    saldos = {}
    versoes = {}
    pendentes = []
    for movimento in Movimento.objects.select_related("lote").order_by("id").iterator():
        lote = movimento.lote
        if not lote.cad_pro_id:
            pendentes.append(movimento.pk)
            continue
        chave = {
            "cad_pro_id": lote.cad_pro_id,
            "cultura": lote.cultura,
            "safra": lote.safra,
            "classificacao_codigo": lote.classificacao_codigo,
            "armazem_id": lote.armazem_id,
        }
        posicao, _ = Posicao.objects.get_or_create(**chave)
        origem = Origem.objects.create(
            tipo="legado",
            chave_idempotencia=f"legado:movimentacao:{movimento.pk}",
            referencia_externa=movimento.referencia_externa,
            hash_requisicao=hashlib.sha256(
                f"legado:{movimento.pk}".encode("utf-8")
            ).hexdigest(),
            metadados={"migration": "0003", "movimentacao_id": movimento.pk},
            criado_por_id=movimento.criado_por_id,
        )
        delta = movimento.quantidade_kg if movimento.tipo == "entrada" else -movimento.quantidade_kg
        saldo_anterior = saldos.get(posicao.pk, Decimal("0.000"))
        saldo_posterior = saldo_anterior + delta
        versao_anterior = versoes.get(posicao.pk, 0)
        versao_posterior = versao_anterior + 1
        Movimento.objects.filter(pk=movimento.pk).update(
            operacao="legado",
            posicao_id=posicao.pk,
            origem_id=origem.pk,
            delta_fisico_kg=delta,
            delta_comprometido_kg=0,
            snapshot_anterior={
                "posicao_id": posicao.pk,
                "saldo_fisico_kg": str(saldo_anterior),
                "saldo_comprometido_kg": "0.000",
                "saldo_disponivel_kg": str(saldo_anterior),
                "versao": versao_anterior,
            },
            snapshot_posterior={
                "posicao_id": posicao.pk,
                "saldo_fisico_kg": str(saldo_posterior),
                "saldo_comprometido_kg": "0.000",
                "saldo_disponivel_kg": str(saldo_posterior),
                "versao": versao_posterior,
            },
        )
        saldos[posicao.pk] = saldo_posterior
        versoes[posicao.pk] = versao_posterior

    if pendentes:
        raise RuntimeError(
            "Não foi possível associar CAD/PRO aos movimentos legados: "
            + ", ".join(str(pk) for pk in pendentes[:20])
        )
    for posicao_id, saldo in saldos.items():
        if saldo < 0:
            raise RuntimeError(f"O ledger legado produz saldo negativo na posição {posicao_id}.")
        Posicao.objects.filter(pk=posicao_id).update(
            saldo_fisico_kg=saldo,
            saldo_comprometido_kg=0,
            versao=versoes[posicao_id],
        )


def reverter(apps, schema_editor):
    Movimento = apps.get_model("graos", "MovimentacaoGraos")
    Origem = apps.get_model("graos", "OrigemSaldoGraos")
    Posicao = apps.get_model("graos", "PosicaoSaldoGraos")
    Reserva = apps.get_model("graos", "ReservaSaldoGraos")

    # O esquema 0001 representa apenas saldo físico. Preserva cada delta físico
    # como movimento legado e remove eventos exclusivamente de compromisso antes
    # de eliminar as tabelas novas, evitando violações de PROTECT.
    somente_compromisso = Movimento.objects.filter(delta_fisico_kg=0)
    somente_compromisso.update(estorno_de_id=None, reserva_id=None)
    somente_compromisso.delete()
    for movimento in Movimento.objects.exclude(delta_fisico_kg=0).iterator():
        delta = movimento.delta_fisico_kg
        Movimento.objects.filter(pk=movimento.pk).update(
            tipo="entrada" if delta > 0 else "saida",
            quantidade_kg=abs(delta),
        )
    Movimento.objects.update(estorno_de_id=None, reserva_id=None)
    Reserva.objects.all().delete()
    Movimento.objects.update(
        operacao=None,
        origem_id=None,
        posicao_id=None,
        delta_fisico_kg=0,
        delta_comprometido_kg=0,
        snapshot_anterior={},
        snapshot_posterior={},
    )
    Origem.objects.all().delete()
    Posicao.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [("graos", "0002_cadpro_saldos_reservas_base")]

    operations = [migrations.RunPython(normalizar, reverter)]

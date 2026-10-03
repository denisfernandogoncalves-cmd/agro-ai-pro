from datetime import timedelta
from decimal import Decimal
from django.db.models import Count, Min, Q, Sum
from django.utils import timezone
from apps.accounts.access import permissoes_do_usuario
from apps.propriedades.models import Propriedade
from apps.graos.models import CargaColhida, PosicaoSaldoGraos
from apps.financeiro.models import LancamentoFinanceiro
from apps.estoque.models import LoteEstoque
from apps.estoque.services import posicao_estoque
from apps.vendas.models import VendaGraos


def total(queryset, campo):
    return str(queryset.aggregate(valor=Sum(campo))["valor"] or Decimal("0"))


def formato_br(valor, casas=3):
    return format(Decimal(valor), f",.{casas}f").replace(",", "_").replace(".", ",").replace("_", ".")


def construir_painel(user, propriedade=None, safra=""):
    autorizacoes = permissoes_do_usuario(user)
    def pode(_user, modulo):
        return "consultar" in autorizacoes.get(modulo, [])
    contagem_avisos = {}
    hoje = timezone.localdate()
    resumo, alertas, saldos = {}, [], []
    def aviso(tipo, titulo, modulo, registro=None, filtros=None, nivel="atenção"):
        contagem_avisos[tipo] = contagem_avisos.get(tipo, 0) + 1
        if contagem_avisos[tipo] > 50:
            return
        alertas.append({"id": f"{tipo}-{registro or len(alertas)}", "tipo": tipo, "titulo": titulo, "modulo": modulo, "registro_id": registro, "filtros": filtros or {}, "nivel": nivel})
    if pode(user, "propriedades"):
        propriedades = Propriedade.objects.all()
        if propriedade:
            propriedades = propriedades.filter(pk=propriedade)
        resumo["propriedades"] = propriedades.count()
        for item in propriedades.filter(Q(proprietario="") | Q(uf="") | Q(municipio=""))[:50]:
            faltam = [nome for nome in ("proprietario", "uf", "municipio") if not getattr(item, nome)]
            aviso("cadastro-incompleto", f"{item.nome}: confira {', '.join(faltam)}.", "propriedades", item.pk, {"search": item.nome})
    if pode(user, "cargas"):
        cargas = CargaColhida.objects.filter(status="ativa")
        if propriedade:
            from apps.graos.selectors import filtrar_cargas_por_produtor
            cargas = filtrar_cargas_por_produtor(cargas, propriedade=propriedade)
        if safra:
            cargas = cargas.filter(safra=safra)
        resumo["cargas"] = cargas.count()
        # Quando filtrada por propriedade, contar somente a parcela produtora.
        if propriedade:
            from apps.graos.models import RateioCargaColhida
            parcelas = RateioCargaColhida.objects.filter(carga__in=cargas, propriedade_id=propriedade)
            sem_rateio = cargas.filter(rateios__isnull=True, propriedade_id=propriedade)
            resumo["producao_kg"] = str(Decimal(total(parcelas, "peso_liquido_kg")) + Decimal(total(sem_rateio, "peso_liquido_kg")))
        else:
            resumo["producao_kg"] = total(cargas, "peso_liquido_kg")
        grupos = cargas.values("data_colheita", "placa", "motorista", "propriedade_id", "cultura", "safra", "peso_bruto_kg").annotate(contagem=Count("id"), registro=Min("id")).filter(contagem__gt=1).order_by("registro")[:50]
        for grupo in grupos:
            aviso("possivel-duplicata-carga", f"{grupo['contagem']} cargas com data, veículo/motorista, produtor, cultura, safra e peso iguais. Confira antes de corrigir.", "cargas", grupo["registro"], {"search": grupo["placa"] or grupo["motorista"]})
    if pode(user, "producao-saldos"):
        posicoes = PosicaoSaldoGraos.objects.all()
        if propriedade:
            posicoes = posicoes.filter(propriedade_id=propriedade)
        if safra:
            posicoes = posicoes.filter(safra=safra)
        resumo["saldo_fisico_kg"] = total(posicoes, "saldo_fisico_kg")
        resumo["saldo_disponivel_kg"] = str(Decimal(resumo["saldo_fisico_kg"]) - Decimal(total(posicoes, "saldo_comprometido_kg")))
        grupos = posicoes.values("propriedade_id", "propriedade__nome", "cultura", "safra").annotate(fisico=Sum("saldo_fisico_kg"), comprometido=Sum("saldo_comprometido_kg")).order_by("propriedade__nome", "cultura", "safra")
        saldos = [{"propriedade_id": item["propriedade_id"], "propriedade": item["propriedade__nome"] or "Sem propriedade", "cultura": item["cultura"], "safra": item["safra"], "fisico_kg": str(item["fisico"]), "disponivel_kg": str(item["fisico"] - item["comprometido"])} for item in grupos[:200]]
        for item in posicoes.filter(saldo_fisico_kg__lt=0).select_related("propriedade")[:50]:
            aviso("saldo-negativo", f"{item.propriedade.nome if item.propriedade else 'Sem propriedade'} · {item.cultura} · {item.safra}: saldo negativo de {formato_br(item.saldo_fisico_kg)} kg. Pode decorrer de sobra técnica; confira o histórico.", "producao-saldos", item.pk, {"propriedade": str(item.propriedade_id or ""), "cultura": item.cultura, "safra": item.safra})
    if pode(user, "vendas"):
        vendas = VendaGraos.objects.filter(excluida_em__isnull=True).exclude(status__in=["cancelada", "rascunho"])
        if propriedade:
            vendas = vendas.filter(posicao__propriedade_id=propriedade)
        if safra:
            vendas = vendas.filter(posicao__safra=safra)
        resumo["vendas_kg"] = total(vendas, "quantidade_kg")
        resumo["entregas_kg"] = str(Decimal(total(vendas, "quantidade_entregue_kg")) - Decimal(total(vendas, "quantidade_devolvida_kg")))
    if pode(user, "financeiro"):
        lancamentos = LancamentoFinanceiro.objects.all()
        if propriedade:
            lancamentos = lancamentos.filter(propriedade_id=propriedade)
        if safra:
            lancamentos = lancamentos.filter(safra=safra)
        pendentes = lancamentos.filter(status="pendente")
        resumo["a_pagar"] = total(pendentes.filter(tipo="pagar"), "valor")
        resumo["a_receber"] = total(pendentes.filter(tipo="receber"), "valor")
        resumo["contas_7_dias"] = pendentes.filter(data_vencimento__range=(hoje, hoje+timedelta(days=7))).count()
        for item in pendentes.filter(data_vencimento__lte=hoje+timedelta(days=7)).order_by("data_vencimento", "id")[:50]:
            vencido = item.data_vencimento < hoje
            aviso("conta-vencida" if vencido else "conta-a-vencer", f"{item.descricao}: {'venceu' if vencido else 'vence'} em {item.data_vencimento.strftime('%d/%m/%Y')} · R$ {formato_br(item.valor, 2)}.", "financeiro", item.pk, {"search": item.descricao, "status": "pendente"}, "urgente" if vencido else "atenção")
        grupos = lancamentos.exclude(status="cancelado").values("tipo", "descricao", "valor", "data_emissao", "data_vencimento", "parceiro_id", "recebedor_nome", "parcela_numero").annotate(contagem=Count("id"), registro=Min("id")).filter(contagem__gt=1).order_by("registro")[:50]
        for grupo in grupos:
            aviso("possivel-duplicata-financeiro", f"{grupo['contagem']} lançamentos com descrição, valor, vencimento, recebedor e parcela iguais: {grupo['descricao']}. Pode ser legítimo; confira.", "financeiro", grupo["registro"], {"search": grupo["descricao"]})
    if pode(user, "estoque"):
        lotes = LoteEstoque.objects.filter(ativo=True, produto__ativo=True)
        posicoes = posicao_estoque(lotes, propriedade=propriedade, safra=safra)
        # Estoque mínimo pertence ao produto, não a cada lote individualmente.
        por_produto = {}
        for item in posicoes:
            por_produto.setdefault(item["produto_id"], {"nome": item["produto"], "saldo": Decimal("0"), "unidade": item["unidade"]})["saldo"] += item["saldo"]
            if item["saldo"] > 0 and (item["vencido"] or item["vence_em_30_dias"]):
                aviso("lote-vencido" if item["vencido"] else "lote-a-vencer", f"{item['produto']} · lote {item['codigo_lote']}: validade {item['data_validade'].strftime('%d/%m/%Y')}.", "estoque", item["lote_id"], {"search": item["codigo_lote"]})
        from apps.estoque.models import ProdutoEstoque
        produtos = ProdutoEstoque.objects.filter(ativo=True)
        if propriedade or safra:
            produtos = produtos.filter(pk__in=por_produto)
        baixos = 0
        for item in produtos:
            saldo = por_produto.get(item.pk, {}).get("saldo", Decimal("0"))
            if saldo < item.estoque_minimo:
                baixos += 1
                aviso("estoque-baixo", f"{item.nome}: saldo {formato_br(saldo)} {item.unidade}, mínimo {formato_br(item.estoque_minimo)} {item.unidade}.", "estoque", item.pk, {"search": item.nome})
        resumo["estoque_baixo"] = baixos
    return {"gerado_em": timezone.now().isoformat(), "resumo": resumo, "saldos": saldos, "alertas": alertas, "limite_por_tipo": 50, "limite_saldos": 200}

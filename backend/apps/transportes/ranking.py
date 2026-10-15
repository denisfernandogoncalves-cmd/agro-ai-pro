from decimal import Decimal, ROUND_HALF_UP
from django.db.models import Q
from apps.accounts.access import pode
from apps.graos.models import CargaColhida, normalizar_placa
from apps.vendas.models import EntregaVendaGraos
from .models import Caminhao, FreteConferido, RemuneracaoMotorista, LancamentoTransporte
from .relatorios import filtros, finalizar, novo, selecionar


def identidade(nome):
    return " ".join(str(nome or "").split()).casefold()


def rankings(resultado, params, usuario):
    financeiro = {}
    for item in resultado["por_motorista"]:
        chave = identidade(item["nome"])
        grupo = financeiro.setdefault(chave, novo(" ".join(item["nome"].split()) or "Sem motorista"))
        for campo in ("receita", "despesas_operacionais", "salario", "comissao"):
            grupo[campo] += Decimal(item[campo])
        grupo["quantidade_lancamentos"] += item["quantidade_lancamentos"]
    remunerados = {identidade(i) for i in selecionar(RemuneracaoMotorista, params).values_list("motorista", flat=True)}
    despesas = {identidade(i) for i in selecionar(LancamentoTransporte, params).filter(tipo="despesa").values_list("motorista", flat=True)}
    financeiros = [dict(finalizar(i), remuneracao_cadastrada=chave in remunerados, despesas_registradas=chave in despesas) for chave, i in financeiro.items()]
    financeiros.sort(key=lambda i: (-Decimal(i["saldo"]), -Decimal(i["receita"]), identidade(i["nome"])))
    eficientes = [dict(i) for i in financeiros if Decimal(i["receita"]) > 0]
    eficientes.sort(key=lambda i: (-Decimal(i["margem"]), -Decimal(i["saldo"]), identidade(i["nome"])))
    f = filtros(params)
    placa = normalizar_placa(f.get("placa", ""))
    if "caminhao_id" in f:
        placa = Caminhao.objects.filter(pk=f["caminhao_id"]).values_list("placa", flat=True).first()
        if placa is None:
            return dict(ranking_financeiro=financeiros, ranking_eficiencia=eficientes, ranking_operacional=[], criterio_ranking=criterio(), documentos_sem_motorista=0)
    fontes = []
    if pode(usuario, "cargas", "consultar"):
        fontes.append(("carga", CargaColhida.objects.filter(status="ativa"), "data_colheita", "peso_liquido_kg"))
    if pode(usuario, "vendas", "consultar"):
        fontes.append(("venda", EntregaVendaGraos.objects.filter(cancelado_em__isnull=True), "data_entrega", "quantidade_kg"))
    consultas = []
    for origem, qs, data, peso in fontes:
        for parametro, lookup in (("data_inicio", "gte"), ("data_fim", "lte")):
            if parametro in f:
                qs = qs.filter(**{f"{data}__{lookup}": f[parametro]})
        consultas.append((origem, qs, peso))
    condicao = Q(pk__in=[])
    for origem, qs, _ in consultas:
        condicao |= Q(**{("carga__in" if origem == "carga" else "entrega__in"): qs})
    associacoes = {("carga" if i.carga_id else "venda", i.carga_id or i.entrega_id): (i.remuneracao.motorista, i.remuneracao.caminhao.placa)
        for i in FreteConferido.objects.filter(condicao).select_related("remuneracao__caminhao")}
    volumes, sem_motorista = {}, 0
    for origem, qs, peso in consultas:
        for item in qs.values("id", "motorista", "placa", peso):
            associado = associacoes.get((origem, item["id"]))
            placa_documento = normalizar_placa(item["placa"]) or (associado[1] if associado else "")
            if placa and placa_documento != placa:
                continue
            nome = associado[0] if associado else item["motorista"]
            chave = identidade(nome)
            if "motorista" in f and chave != identidade(f["motorista"]):
                continue
            if not chave:
                sem_motorista += 1
                continue
            grupo = volumes.setdefault(chave, {"nome": " ".join(nome.split()), "documentos": 0, "peso_kg": Decimal(0)})
            grupo["documentos"] += 1
            grupo["peso_kg"] += item[peso]
    operacionais = []
    for i in volumes.values():
        toneladas = i["peso_kg"] / Decimal(1000)
        media = toneladas / i["documentos"]
        operacionais.append({"nome": i["nome"], "documentos": i["documentos"],
            "toneladas": str(toneladas.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)),
            "toneladas_por_documento": str(media.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)), "_media": media})
    operacionais.sort(key=lambda i: (-i["_media"], -Decimal(i["toneladas"]), identidade(i["nome"])))
    for i in operacionais:
        del i["_media"]
    return dict(ranking_financeiro=financeiros, ranking_eficiencia=eficientes,
        ranking_operacional=operacionais, criterio_ranking=criterio(), documentos_sem_motorista=sem_motorista)


def criterio():
    return ("Financeiro: receita registrada de Transportes menos despesas operacionais, salário e comissão, "
        "incluindo fretes marcados para adicionar. Eficiência financeira: resultado ÷ receita × 100; sem receita, "
        "não há margem calculável. Operacional: toneladas médias por documento ativo de cargas colhidas e entregas "
        "de vendas acessíveis; não é contagem de viagens únicas nem mede consumo, distância, capacidade ou horas. "
        "Frete informado na conferência não cria receita: registre a receita correspondente em Transportes uma única vez. "
        "Resultado considera custos cadastrados; custos ausentes não são estimados. A conferência indica se há "
        "remuneração mensal e despesa operacional registradas, sem certificar que todos os custos foram informados. Para comparação mensal, use mês "
        "completo: salário e comissão são contabilizados no último dia da competência.")

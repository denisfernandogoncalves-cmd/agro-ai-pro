import calendar

from datetime import date

from decimal import Decimal



from rest_framework.exceptions import ValidationError

from .models import LancamentoTransporte, RemuneracaoMotorista





def filtros(params):

    resultado = {}

    for chave in ("data_inicio", "data_fim"):

        if params.get(chave):

            try:

                resultado[chave] = date.fromisoformat(params[chave])

            except (TypeError, ValueError):

                raise ValidationError({chave: "Informe uma data válida (AAAA-MM-DD)."})

    if resultado.get("data_inicio", date.min) > resultado.get("data_fim", date.max):

        raise ValidationError("A data inicial deve ser anterior ou igual à final.")

    if params.get("caminhao"):

        try:

            resultado["caminhao_id"] = int(params["caminhao"])

        except (TypeError, ValueError):

            raise ValidationError({"caminhao": "Caminhão inválido."})

    for chave in ("motorista", "placa"):

        if params.get(chave):

            resultado[chave] = params[chave].strip()

    return resultado





def selecionar(model, params):

    f = filtros(params)

    qs = model.objects.select_related("caminhao")

    if "caminhao_id" in f:

        qs = qs.filter(caminhao_id=f["caminhao_id"])

    if "motorista" in f:

        qs = qs.filter(motorista__iexact=f["motorista"])

    if "placa" in f:

        qs = qs.filter(caminhao__placa__iexact=f["placa"].upper().replace("-", ""))

    campo = "competencia" if model is RemuneracaoMotorista else "data"

    for parametro, operador in (("data_inicio", "gte"), ("data_fim", "lte")):

        if parametro in f:

            limite = f[parametro]

            if model is RemuneracaoMotorista:

                # Remuneração é contabilizada no último dia do mês, sem rateio implícito.

                qs = qs.filter(competencia__gte=limite.replace(day=1)) if operador == "gte" else qs.filter(competencia__lte=limite.replace(day=1))

            else:

                qs = qs.filter(**{f"{campo}__{operador}": limite})

    if model is RemuneracaoMotorista and "data_fim" in f:

        limite = f["data_fim"]

        if limite.day < calendar.monthrange(limite.year, limite.month)[1]:

            qs = qs.exclude(competencia=limite.replace(day=1))

    return qs





def novo(nome):

    return dict(nome=nome, receita=Decimal(0), despesas_operacionais=Decimal(0), salario=Decimal(0), comissao=Decimal(0), quantidade_lancamentos=0)





def finalizar(item):

    item = dict(item)

    item["despesas"] = item["despesas_operacionais"] + item["salario"] + item["comissao"]

    item["saldo"] = item["receita"] - item["despesas"]

    item["margem"] = (item["saldo"] * 100 / item["receita"]).quantize(Decimal("0.01")) if item["receita"] else None

    return {k: str(v) if isinstance(v, Decimal) else v for k, v in item.items()}





def relatorio(params):

    total = novo("Total")

    placas, motoristas, meses, categorias = {}, {}, {}, {}

    for item in selecionar(LancamentoTransporte, params):

        destinos = [total, placas.setdefault(item.caminhao.placa, novo(item.caminhao.placa)), motoristas.setdefault(item.motorista, novo(item.motorista)), meses.setdefault(item.data.strftime("%Y-%m"), novo(item.data.strftime("%Y-%m")))]

        campo = "receita" if item.tipo == "receita" else "despesas_operacionais"

        for grupo in destinos:

            grupo[campo] += item.total

            grupo["quantidade_lancamentos"] += 1

        categoria = f"{item.tipo}: {item.descricao}"

        categorias[categoria] = categorias.get(categoria, Decimal(0)) + item.total

    for item in selecionar(RemuneracaoMotorista, params):

        destinos = [total, placas.setdefault(item.caminhao.placa, novo(item.caminhao.placa)), motoristas.setdefault(item.motorista, novo(item.motorista)), meses.setdefault(item.competencia.strftime("%Y-%m"), novo(item.competencia.strftime("%Y-%m")))]

        for grupo in destinos:

            grupo["salario"] += item.salario

            grupo["comissao"] += item.valor_comissao

    ranking = lambda dados: [finalizar(i) for i in sorted(dados.values(), key=lambda i: (-i["receita"], i["nome"]))]

    return dict(resumo=finalizar(total), por_placa=ranking(placas), por_motorista=ranking(motoristas), por_mes=[finalizar(meses[k]) for k in sorted(meses)], categorias=[dict(nome=k, total=str(v)) for k, v in sorted(categorias.items(), key=lambda i: (-i[1], i[0]))], criterio_remuneracao="Salário manual e comissão pelo percentual sobre receitas menos despesas de AREIA e PEDRA, contabilizados no último dia do mês de competência. Saldo considera somente os custos registrados; não representa saldo bancário.")

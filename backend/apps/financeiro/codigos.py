"""Leitura local FEBRABAN; não consulta nem paga títulos."""
from datetime import date, timedelta
from decimal import Decimal
from functools import lru_cache
import json
from pathlib import Path
import re

SEGMENTOS = {
    "1": "Prefeituras", "2": "Saneamento", "3": "Energia elétrica e gás",
    "4": "Telecomunicações", "5": "Órgãos governamentais",
    "6": "Carnês e assemelhados", "7": "Multas de trânsito", "9": "Uso do banco",
}


class CodigoPagamentoInvalido(ValueError):
    pass


def modulo10(numero):
    produtos = (int(d) * (2 if i % 2 == 0 else 1) for i, d in enumerate(reversed(numero)))
    return (-sum(p // 10 + p % 10 for p in produtos)) % 10


def modulo11(numero, *, arrecadacao=False):
    resto = sum(int(d) * (2 + i % 8) for i, d in enumerate(reversed(numero))) % 11
    if arrecadacao:
        return 0 if resto in (0, 1) else 11 - resto
    resultado = 11 - resto
    return 1 if resultado in (0, 10, 11) else resultado


def _validar_digito(numero, digito, calculo):
    if calculo(numero) != int(digito):
        raise CodigoPagamentoInvalido("Dígito verificador inválido. Leia o documento novamente.")


def _valor(numero):
    return f"{Decimal(numero) / 100:.2f}" if int(numero) else None


@lru_cache(maxsize=1)
def _bancos():
    # Catálogo público versionado: nenhuma consulta externa recebe o boleto.
    return json.loads(Path(__file__).with_name("bancos_str.json").read_text(encoding="utf-8-sig"))["bancos"]


def _detalhes_itau(codigo):
    """CNAB 400 Itaú, seção 7.3.2 e anexo 4; somente carteiras conhecidas."""
    carteira = codigo[19:22]
    if carteira not in {"104", "108", "109", "112", "115", "121", "147", "150", "180", "188", "191"}:
        return []
    agencia, conta, numero = codigo[31:35], codigo[35:40], codigo[22:30]
    base_numero = carteira + numero if carteira == "150" else agencia + conta + carteira + numero
    if (codigo[41:] != "000" or modulo10(base_numero) != int(codigo[30])
            or modulo10(agencia + conta) != int(codigo[40])):
        return []
    return [
        {"campo": "Agência do beneficiário", "valor": agencia},
        {"campo": "Conta do beneficiário", "valor": f"{conta}-{codigo[40]}"},
        {"campo": "Carteira", "valor": carteira},
        {"campo": "Nosso número", "valor": f"{numero}-{codigo[30]}"},
    ]


def ler_codigo_pagamento(entrada):
    if not isinstance(entrada, str) or len(entrada) > 100 or not re.fullmatch(r"[0-9.\s-]+", entrada):
        raise CodigoPagamentoInvalido("Informe somente números, espaços, pontos ou hífens do código.")
    codigo = re.sub(r"[.\s-]", "", entrada)
    if len(codigo) not in (44, 47, 48):
        raise CodigoPagamentoInvalido("Use código de barras com 44 dígitos ou linha digitável com 47 ou 48 dígitos.")
    if len(set(codigo)) == 1:
        raise CodigoPagamentoInvalido("Código de pagamento inválido.")
    tamanho_original = len(codigo)
    if len(codigo) == 47:
        for inicio, fim in ((0, 9), (10, 20), (21, 31)):
            _validar_digito(codigo[inicio:fim], codigo[fim], modulo10)
        codigo = codigo[:4] + codigo[32] + codigo[33:] + codigo[4:9] + codigo[10:20] + codigo[21:31]
    elif len(codigo) == 48:
        if not codigo.startswith("8") or codigo[2] not in "6789":
            raise CodigoPagamentoInvalido("Linha de arrecadação não reconhecida.")
        calculo = modulo10 if codigo[2] in "67" else lambda n: modulo11(n, arrecadacao=True)
        for inicio in range(0, 48, 12):
            _validar_digito(codigo[inicio:inicio + 11], codigo[inicio + 11], calculo)
        codigo = "".join(codigo[i:i + 11] for i in range(0, 48, 12))
    resultado = {
        "codigo_barras": codigo, "tipo": "boleto", "banco_codigo": None, "banco_nome": None,
        "segmento": None, "identificacao_emissor": None, "valor": None,
        "vencimentos_possiveis": [], "avisos": [],
    }
    arrecadacao = tamanho_original == 48 or (tamanho_original == 44 and codigo.startswith("8"))
    if tamanho_original == 44 and codigo.startswith("8") and codigo[3] == "9":
        # Instituições com código 8xx também podem emitir boletos bancários.
        banco_valido = modulo11(codigo[:4] + codigo[5:]) == int(codigo[4])
        if banco_valido:
            if codigo[1] in SEGMENTOS and codigo[2] in "6789":
                calculo = modulo10 if codigo[2] in "67" else lambda n: modulo11(n, arrecadacao=True)
                if calculo(codigo[:3] + codigo[4:]) == int(codigo[3]):
                    raise CodigoPagamentoInvalido("Formato ambíguo. Use a linha digitável impressa no documento.")
            arrecadacao = False
    if arrecadacao:
        if codigo[1] not in SEGMENTOS or codigo[2] not in "6789":
            raise CodigoPagamentoInvalido("Segmento ou identificador de valor da arrecadação não suportado.")
        calculo = modulo10 if codigo[2] in "67" else lambda n: modulo11(n, arrecadacao=True)
        _validar_digito(codigo[:3] + codigo[4:], codigo[3], calculo)
        resultado.update(
            tipo="arrecadacao", segmento=SEGMENTOS[codigo[1]],
            identificacao_emissor=codigo[15:23] if codigo[1] == "6" else codigo[15:19],
            valor=_valor(codigo[4:15]) if codigo[2] in "68" else None,
        )
        # O campo livre pode conter datas, mas não há marcador que confirme a interpretação.
        resultado["avisos"].append("Informe o vencimento impresso na conta; o campo livre não permite identificá-lo com segurança.")
        if codigo[2] in "79":
            resultado["avisos"].append("O código contém referência ou índice, não um valor em reais.")
    else:
        if codigo[:3] == "000" or codigo[3] != "9":
            raise CodigoPagamentoInvalido("Somente boletos bancários em reais são suportados.")
        _validar_digito(codigo[:4] + codigo[5:], codigo[4], modulo11)
        resultado.update(banco_codigo=codigo[:3], banco_nome=_bancos().get(codigo[:3]), valor=_valor(codigo[9:19]))
        fator = int(codigo[5:9])
        if fator >= 1000:
            resultado["vencimentos_possiveis"] = [
                (date(2025, 2, 22) + timedelta(days=fator - 1000)).isoformat(),
                (date(1997, 10, 7) + timedelta(days=fator)).isoformat(),
            ]
            resultado["avisos"].append("O fator de vencimento foi reiniciado em 2025. Escolha a data que consta no boleto.")
        else:
            resultado["avisos"].append("Vencimento não determinado com segurança. Informe a data impressa no boleto.")
        resultado["avisos"].append("Confira o valor impresso: títulos de valor elevado podem usar também o campo de vencimento.")
    if resultado["valor"] is None:
        resultado["avisos"].append("Valor em reais não disponível no código. Preencha manualmente.")
    if resultado["tipo"] == "boleto":
        campos = [codigo[:4] + codigo[19:24], codigo[24:34], codigo[34:44]]
        linha = "".join(campo + str(modulo10(campo)) for campo in campos) + codigo[4] + codigo[5:19]
        linha_formatada = f"{linha[:5]}.{linha[5:10]} {linha[10:15]}.{linha[15:21]} {linha[21:26]}.{linha[26:32]} {linha[32]} {linha[33:]}"
        detalhes = [
            {"campo": "Moeda", "valor": "Real (BRL)"},
            {"campo": "Fator de vencimento", "valor": codigo[5:9]},
            {"campo": "Campo livre do banco", "valor": codigo[19:]},
        ]
        nome = resultado["banco_nome"]
        resultado["descricao_sugerida"] = f"Boleto bancário · {nome} ({codigo[:3]})" if nome else f"Boleto bancário · banco {codigo[:3]}"
        especificos = _detalhes_itau(codigo) if codigo[:3] == "341" else []
        detalhes = especificos + detalhes
        if not especificos:
            resultado["avisos"].append("Agência, conta, carteira e nosso número não identificados neste formato; confira o campo livre no documento.")
        if not nome:
            resultado["avisos"].append("Nome do banco não encontrado no catálogo local; o código foi preservado.")
    else:
        linha = "".join(codigo[i:i + 11] + str(calculo(codigo[i:i + 11])) for i in range(0, 44, 11))
        linha_formatada = " ".join(linha[i:i + 12] for i in range(0, 48, 12))
        detalhes = [
            {"campo": "Código do segmento", "valor": codigo[1]},
            {"campo": "Tipo de valor", "valor": "Valor em reais" if codigo[2] in "68" else "Referência ou índice (não é valor em reais)"},
            {"campo": "Valor ou referência original", "valor": codigo[4:15]},
            {"campo": "Tipo de identificação do emissor", "valor": "Raiz do CNPJ (8 dígitos; não é CNPJ completo)" if codigo[1] == "6" else "Código da empresa/órgão"},
            {"campo": "Campo livre do emissor", "valor": codigo[23:] if codigo[1] == "6" else codigo[19:]},
        ]
        resultado["descricao_sugerida"] = f"{resultado['segmento']} · emissor {resultado['identificacao_emissor']}"
    resultado.update(
        linha_digitavel=linha,
        linha_digitavel_formatada=linha_formatada,
        formato_entrada=f"{'Código de barras' if tamanho_original == 44 else 'Linha digitável'} ({tamanho_original} dígitos)",
        detalhes=detalhes,
    )
    resultado["avisos"].append("Nome do recebedor, CPF/CNPJ completo, juros, descontos e situação de pagamento não são obtidos apenas com o leitor. O banco identificado não é o recebedor.")
    return resultado

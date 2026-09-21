"""Conversão de embalagens para a unidade base do estoque."""
from decimal import Decimal, ROUND_HALF_UP


def calcular_compra(quantidade_embalagens, conteudo_embalagem, custo_embalagem):
    quantidade = Decimal(str(quantidade_embalagens))
    conteudo = Decimal(str(conteudo_embalagem))
    custo = Decimal(str(custo_embalagem))
    if not all(valor.is_finite() for valor in (quantidade, conteudo, custo)):
        raise ValueError("Informe números finitos para quantidade, conteúdo e custo.")
    if quantidade <= 0 or conteudo <= 0 or custo < 0:
        raise ValueError("Quantidade e conteúdo devem ser positivos; custo não pode ser negativo.")
    total_quantidade = quantidade * conteudo
    if total_quantidade != total_quantidade.quantize(Decimal("0.001")):
        raise ValueError("A quantidade total deve ter no máximo três casas decimais.")
    if total_quantidade >= Decimal("100000000000"):
        raise ValueError("Quantidade total acima do limite do estoque.")
    custo_base = (custo / conteudo).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    if custo_base >= Decimal("10000000000"):
        raise ValueError("Valor por litro ou kg acima do limite do estoque.")
    return {
        "quantidade": total_quantidade.quantize(Decimal("0.001")),
        "custo_unitario": custo_base,
        "valor_total": (quantidade * custo).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
    }

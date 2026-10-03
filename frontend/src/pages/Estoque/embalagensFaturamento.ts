import { ItemFaturamento } from "../../api/faturamentoInsumos";

function decimal(valor: string) {
  valor = valor.trim().replace(",", ".");
  if (!/^\d+(?:\.\d+)?$/.test(valor.trim())) return null;
  const [inteiro, fracao = ""] = valor.trim().split(".");
  return { valor: BigInt(inteiro + fracao), escala: 10n ** BigInt(fracao.length) };
}

export function sugerirEmbalagens(area: string, dosagem: string, conteudo: string) {
  const a = decimal(area), d = decimal(dosagem), c = decimal(conteudo);
  if (!a || !d || !c || a.valor <= 0n || c.valor <= 0n) return "";
  const numerador = a.valor * d.valor * c.escala;
  const denominador = a.escala * d.escala * c.valor;
  return String((numerador + denominador - 1n) / denominador);
}

export function quantidadeParaEnviar(item: ItemFaturamento, dosagem: string, conteudo: string, editada: boolean) {
  return editada ? item.quantidade_embalagens : sugerirEmbalagens(item.area_alqueires, dosagem, conteudo);
}

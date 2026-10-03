export function formatarNumero(valor: string | number | null | undefined, casas = 3) {
  if (valor === null || valor === undefined || valor === "") return "—";
  const numero = Number(valor);
  return Number.isFinite(numero) ? numero.toLocaleString("pt-BR", {maximumFractionDigits:casas}) : "—";
}
export const formatarPercentual = (valor: string | number) => `${formatarNumero(valor, 3)}%`;

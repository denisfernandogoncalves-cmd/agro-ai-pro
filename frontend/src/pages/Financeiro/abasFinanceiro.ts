export type AbaFinanceiro = "todos" | "pagar" | "receber" | "liquidados";
export function abaDosFiltros(filtros: { tipo: string; status: string }): AbaFinanceiro {
  if (filtros.status === "liquidado" && !filtros.tipo) return "liquidados";
  if (filtros.status === "pendente" && filtros.tipo === "pagar") return "pagar";
  if (filtros.status === "pendente" && filtros.tipo === "receber") return "receber";
  return "todos";
}
export function filtrosDaAba<T extends { tipo: string; status: string }>(aba: string, filtros: T): T {
  return { ...filtros, tipo: aba === "pagar" || aba === "receber" ? aba : "", status: aba === "liquidados" ? "liquidado" : aba === "pagar" || aba === "receber" ? "pendente" : "" };
}

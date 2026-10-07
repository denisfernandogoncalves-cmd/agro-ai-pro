export function restanteEntrega(contratado: string | number, entregue: string | number, cancelado: string | number = 0) {
  return Math.max(0, Math.round((Number(contratado) - Number(entregue) - Number(cancelado)) * 1000) / 1000);
}
export function diferencaLiquidacao(valor: string | number, liquidado: string | number | null) {
  return Math.round((Number(valor) - Number(liquidado ?? 0)) * 100) / 100;
}
export function diasAte(data: string, referencia: string) {
  return Math.round((Date.parse(`${data}T00:00:00Z`) - Date.parse(`${referencia}T00:00:00Z`)) / 86400000);
}
export function prioridadeValidade<T extends {data_validade: string | null}>(itens: T[]) {
  return [...itens].sort((a,b)=>(a.data_validade || '9999-12-31').localeCompare(b.data_validade || '9999-12-31'));
}

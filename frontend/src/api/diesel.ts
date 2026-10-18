import { api } from "./propriedades";
import type { Pagina } from "./transportes";

export type CompraDieselInput = { data: string; fornecedor: string; produtor: string; documento: string; tipo: string; litros: string; valor_unitario: string; prazo_dias: number | null; pagamento: string; observacoes: string };
export type CompraDiesel = CompraDieselInput & { id: number; valor_total: string; vencimento: string | null; atualizado_em: string; conta_pagar: number | null };
export type ResumoDiesel = { compras: number; litros: string; valor_total: string };
const base = "/transportes/compras-diesel/";
export const consultarVencimentoDiesel = async (data: string, prazo_dias: number, signal?: AbortSignal) => (await api.get<{ vencimento: string }>(base + 'vencimento/', { params: { data, prazo_dias }, signal })).data.vencimento;
export async function consultarComprasDiesel(filtros: Record<string, string>, page: number, signal?: AbortSignal) {
  const [lista, resumo] = await Promise.all([
    api.get<Pagina<CompraDiesel>>(base, { params: { ...filtros, page }, signal }),
    api.get<ResumoDiesel>(base + "resumo/", { params: filtros, signal }),
  ]);
  return { lista: lista.data, resumo: resumo.data };
}
export const salvarCompraDiesel = async (id: number | null, dados: CompraDieselInput, versao?: string) => (await (id
  ? api.patch<CompraDiesel>(base + `${id}/`, { ...dados, atualizado_em_original: versao })
  : api.post<CompraDiesel>(base, dados))).data;
export const excluirCompraDiesel = async (compra: CompraDiesel) => {
  await api.delete(base + `${compra.id}/`, { data: { atualizado_em_original: compra.atualizado_em } });
};
export type PrecoSilo = { compra: number; data_compra: string; valor_unitario: string; tipo_diesel: string };
export const consultarPrecoSilo = async (data: string, tipo_diesel: string, signal?: AbortSignal) => (await api.get<PrecoSilo>("/transportes/lancamentos/preco-silo/", { params: { data, tipo_diesel }, signal })).data;

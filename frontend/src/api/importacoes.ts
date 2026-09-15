import { api } from "./propriedades";

export type LoteImportacao = {
  id: number; arquivo_nome: string; status: string; total_linhas: number;
  total_erros: number; total_advertencias: number; pode_confirmar: boolean;
};
export type LinhaImportacao = {
  id: number; planilha: string; linha_origem: number; status: string;
  propriedade_nome?: string; lote_graos_codigo?: string;
  dados_normalizados: Record<string, unknown>; erros: string[]; advertencias: string[];
};
export type Pagina<T> = { results: T[]; next: string | null; previous: string | null; count: number };
const base = "/importacoes/";
export async function listarLotes(page = 1) {
  return (await api.get<Pagina<LoteImportacao>>(`${base}lotes/`, { params: { page } })).data;
}
export async function consultarLote(id: number) {
  return (await api.get<LoteImportacao>(`${base}lotes/${id}/`)).data;
}
export async function listarLinhas(lote: number, page = 1) {
  return (await api.get<Pagina<LinhaImportacao>>(`${base}linhas/`, { params: { lote, page } })).data;
}
export async function previewPlanilha(arquivo: File) {
  const corpo = new FormData();
  corpo.append("arquivo", arquivo);
  return (await api.post<{ lote: LoteImportacao }>(`${base}lotes/preview/`, corpo)).data;
}
export async function confirmarImportacao(id: number, chave: string) {
  return (await api.post<{ total_movimentacoes_criadas: number; replay_idempotente: boolean }>(
    `${base}lotes/${id}/confirmar/`, { confirmar: true, idempotency_key: chave },
  )).data;
}
export function loteElegivel(lote: LoteImportacao) {
  return lote.pode_confirmar && lote.total_erros === 0 && lote.total_linhas > 0
    && ["concluido", "pronto_confirmacao", "falhou"].includes(lote.status);
}

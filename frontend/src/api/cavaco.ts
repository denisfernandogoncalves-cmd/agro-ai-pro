import { api } from "./propriedades";

export type CargaCavacoInput = {
  data: string; motorista: string; fornecedor: string; placa: string;
  valor_tonelada: string; peso_bruto: string; tara: string;
  pago: boolean; observacoes: string;
  data_vencimento?: string | null;
};
export type CargaCavaco = CargaCavacoInput & {
  id: number; peso_liquido: string; total: string; criado_em: string;
  conta_pagar?: number | null; pagamento_financeiro?: string | null;
};
export type FiltrosCavaco = { search: string; pago: string; data_inicio: string; data_fim: string };

export async function listarCavaco(filtros: FiltrosCavaco) {
  const { data } = await api.get<CargaCavaco[] | { results: CargaCavaco[] }>("/estoque/cavaco/", { params: filtros });
  return Array.isArray(data) ? data : data.results;
}
export async function salvarCavaco(dados: CargaCavacoInput, id?: number) {
  const payload = { ...dados, data_vencimento: dados.data_vencimento || null };
  return (id ? await api.patch<CargaCavaco>(`/estoque/cavaco/${id}/`, payload) : await api.post<CargaCavaco>("/estoque/cavaco/", payload)).data;
}
export async function excluirCavaco(id: number) {
  await api.delete(`/estoque/cavaco/${id}/`);
}
export async function abrirRomaneioCavaco(id: number) {
  const janela = window.open("", "_blank");
  if (!janela) throw new Error("Permita abrir novas janelas para imprimir o romaneio.");
  janela.opener = null;
  janela.document.title = "Carregando romaneio…";
  try {
    const { data } = await api.get<string>(`/estoque/cavaco/${id}/romaneio/`, { responseType: "text" });
    const url = URL.createObjectURL(new Blob([data], { type: "text/html;charset=utf-8" }));
    janela.location.replace(url);
    window.setTimeout(() => URL.revokeObjectURL(url), 60000);
  } catch (erro) { janela.close(); throw erro; }
}

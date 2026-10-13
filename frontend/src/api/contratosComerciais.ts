import { api } from "./propriedades";

export type UnidadePrecoContrato = "kg" | "sc";
export type ContratoComercial = { id: number; empresa: string; numero: string; quantidade_kg: string | null; produto: string; preco_venda: string | null; unidade_preco: UnidadePrecoContrato; ativo: boolean; versao: number; alerta_restante_kg: string | null; cotas_cadpro: {cad_pro:string;quantidade_kg:string}[]; calendario_entregas: {cad_pro:string;quantidade_kg:string;data:string}[] };
export type DadosContrato = { empresa: string; numero: string; quantidade_kg: string; produto: string; preco_venda: string | null; unidade_preco: UnidadePrecoContrato };

export async function carregarContratos() {
  return (await api.get<ContratoComercial[]>("/comercial/contratos/")).data;
}
export async function salvarContrato(dados: DadosContrato, id?: number, versao?: number, justificativa?: string) {
  return id
    ? (await api.patch<ContratoComercial>(`/comercial/contratos/${id}/`, {...dados,versao,justificativa})).data
    : (await api.post<ContratoComercial>("/comercial/contratos/", {...dados,versao,justificativa})).data;
}
export async function excluirContrato(id: number, versao: number) {
  await api.delete(`/comercial/contratos/${id}/`, {data:{versao,justificativa:"Inativação confirmada pelo usuário; histórico preservado."}});
}
export async function reativarContrato(id: number, versao: number) {
  await api.patch(`/comercial/contratos/${id}/`, { ativo: true, versao, justificativa: "Reativação solicitada pelo usuário." });
}

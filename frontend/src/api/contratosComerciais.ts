import { api } from "./propriedades";

export type ContratoComercial = { id: number; empresa: string; numero: string; quantidade_kg: string | null; produto: string; ativo: boolean };
export type DadosContrato = { empresa: string; numero: string; quantidade_kg: string; produto: string };

export async function carregarContratos() {
  return (await api.get<ContratoComercial[]>("/comercial/contratos/")).data;
}
export async function salvarContrato(dados: DadosContrato, id?: number) {
  return id
    ? (await api.patch<ContratoComercial>(`/comercial/contratos/${id}/`, dados)).data
    : (await api.post<ContratoComercial>("/comercial/contratos/", dados)).data;
}
export async function excluirContrato(id: number) {
  await api.delete(`/comercial/contratos/${id}/`);
}
export async function reativarContrato(id: number) {
  await api.patch(`/comercial/contratos/${id}/`, { ativo: true });
}

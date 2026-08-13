import { api } from "./propriedades";
import { PosicaoSaldo } from "./producaoSaldos";

export type StatusVenda = "rascunho" | "confirmada" | "parcial" | "entregue" | "cancelada";

export type MovimentoVenda = {
  id: number;
  quantidade_kg: string;
  data_entrega?: string;
  data_devolucao?: string;
  referencia_externa: string;
  movimentacao_id: number;
};

export type VendaGraos = {
  id: number;
  numero_contrato: string;
  cliente_nome: string;
  status: StatusVenda;
  posicao: number;
  lote_operacional: number;
  lote_operacional_codigo: string;
  origem_fisica_alocada: boolean;
  cad_pro: string;
  cad_pro_codigo: string;
  cultura: string;
  safra: string;
  classificacao_codigo: string;
  armazem_nome: string;
  propriedade_nome: string;
  quantidade_kg: string;
  quantidade_reservada_kg: string;
  quantidade_entregue_kg: string;
  quantidade_devolvida_kg: string;
  quantidade_cancelada_kg: string;
  quantidade_aberta_kg: string;
  data_contrato: string;
  data_limite_entrega: string | null;
  observacoes: string;
  entregas: MovimentoVenda[];
  devolucoes: MovimentoVenda[];
};

export type FiltrosVenda = {
  search?: string;
  status?: string;
  cad_pro?: string;
  cultura?: string;
  safra?: string;
  classificacao_codigo?: string;
  armazem?: string;
};

export type NovaVenda = {
  numero_contrato: string;
  cliente_nome: string;
  posicao: number;
  quantidade_kg: string;
  data_contrato: string;
  data_limite_entrega: string | null;
  observacoes: string;
};

const cabecalho = (chave: string) => ({ headers: { "Idempotency-Key": chave } });

export async function carregarVendas(filtros: FiltrosVenda = {}) {
  const [vendas, posicoes] = await Promise.all([
    api.get<VendaGraos[]>("/comercial/vendas/", { params: filtros }),
    api.get<PosicaoSaldo[]>("/graos/saldos/"),
  ]);
  return { vendas: vendas.data, posicoes: posicoes.data };
}

export async function criarVenda(dados: NovaVenda, chave: string) {
  return (await api.post<VendaGraos>("/comercial/vendas/", dados, cabecalho(chave))).data;
}

export async function confirmarVenda(id: number, chave: string) {
  return (await api.post<VendaGraos>(`/comercial/vendas/${id}/confirmar/`, {}, cabecalho(chave))).data;
}

export async function cancelarVenda(id: number, observacoes: string, chave: string) {
  return (await api.post<VendaGraos>(`/comercial/vendas/${id}/cancelar/`, { observacoes }, cabecalho(chave))).data;
}

export async function entregarVenda(id: number, quantidade_kg: string, data_movimento: string, chave: string) {
  return (await api.post<VendaGraos>(`/comercial/vendas/${id}/entregar/`, { quantidade_kg, data_movimento }, cabecalho(chave))).data;
}

export async function devolverVenda(id: number, quantidade_kg: string, data_movimento: string, chave: string) {
  return (await api.post<VendaGraos>(`/comercial/vendas/${id}/devolver/`, { quantidade_kg, data_movimento }, cabecalho(chave))).data;
}

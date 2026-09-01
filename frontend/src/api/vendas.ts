import { api, listarPropriedades } from "./propriedades";
import { PosicaoSaldo } from "./producaoSaldos";
import { carregarContratos } from "./contratosComerciais";
import { ArmazemGraos, CADPro } from "./cargasColhidas";

export type StatusVenda = "rascunho" | "confirmada" | "parcial" | "entregue" | "cancelada";

export type MovimentoVenda = {
  id: number;
  cancelado_em: string | null;
  observacoes: string;
  quantidade_kg: string;
  data_entrega?: string;
  data_devolucao?: string;
  referencia_externa: string;
  destino?: string;
  placa?: string;
  motorista?: string;
  nota_produtor?: string;
  nota_empresa?: string;
  movimentacao_id: number;
};

export type DadosEntrega = {
  quantidade_kg: string;
  data_movimento: string;
  destino: string;
  placa: string;
  motorista: string;
  nota_produtor: string;
  nota_empresa: string;
};

export type VendaGraos = {
  id: number;
  contrato: number | null;
  versao: number;
  excluida_em: string | null;
  alteracoes: { id: number; tipo: string; motivo: string; criado_em: string; usuario: string }[];
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
  propriedade: number | null;
  propriedade_nome: string | null;
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
  mostrar_excluidas?: string;
  propriedade?: string;
  search?: string;
  status?: string;
  cad_pro?: string;
  cultura?: string;
  safra?: string;
  classificacao_codigo?: string;
  armazem?: string;
};

export type NovaVenda = {
  contrato?: number;
  numero_contrato: string;
  cliente_nome: string;
  posicao: number;
  quantidade_kg: string;
  data_contrato: string;
  data_limite_entrega: string | null;
  observacoes: string;
};

export type DadosNovaPosicao = { propriedade: number; cad_pro: string; cultura: string; safra: string; classificacao_codigo: string; armazem: number };
export type RegistroVenda = Omit<NovaVenda, "posicao"> & { posicao?: number; nova_posicao?: DadosNovaPosicao };

const cabecalho = (chave: string) => ({ headers: { "Idempotency-Key": chave } });

export async function carregarVendas(filtros: FiltrosVenda = {}) {
  const [vendas, posicoes, contratos, propriedades, cadpros, armazens] = await Promise.all([
    api.get<VendaGraos[]>("/comercial/vendas/", { params: filtros }),
    api.get<PosicaoSaldo[]>("/graos/saldos/"),
    carregarContratos(),
    listarPropriedades(),
    api.get<CADPro[]>("/cadpros/", { params: { ativo: true } }),
    api.get<ArmazemGraos[]>("/graos/armazens/", { params: { ativo: true } }),
  ]);
  return { vendas: vendas.data, posicoes: posicoes.data, contratos, propriedades, cadpros: cadpros.data, armazens: armazens.data };
}

export type AlvoEdicaoVenda = { venda: VendaGraos; natureza: "venda" | "entrega" | "devolucao"; movimento?: MovimentoVenda; excluir: boolean };

export async function alterarLancamentoVenda(alvo: AlvoEdicaoVenda, dados: Record<string, unknown>, chave: string) {
  const sufixo = alvo.natureza === "venda" ? "" : `${alvo.natureza === "entrega" ? "entregas" : "devolucoes"}/${alvo.movimento!.id}/`;
  const url = `/comercial/vendas/${alvo.venda.id}/${sufixo}`;
  const payload = { ...dados, versao: alvo.venda.versao };
  return alvo.excluir
    ? (await api.delete<VendaGraos>(url, { ...cabecalho(chave), data: payload })).data
    : (await api.patch<VendaGraos>(url, payload, cabecalho(chave))).data;
}

export async function criarVenda(dados: RegistroVenda, chave: string) {
  return (await api.post<VendaGraos>("/comercial/vendas/", dados, cabecalho(chave))).data;
}

export async function registrarVendaComSaida(dados: RegistroVenda & DadosEntrega, chave: string) {
  return (await api.post<VendaGraos>("/comercial/vendas/registrar-saida/", dados, cabecalho(chave))).data;
}

export async function confirmarVenda(id: number, chave: string) {
  return (await api.post<VendaGraos>(`/comercial/vendas/${id}/confirmar/`, {}, cabecalho(chave))).data;
}

export async function cancelarVenda(id: number, observacoes: string, chave: string) {
  return (await api.post<VendaGraos>(`/comercial/vendas/${id}/cancelar/`, { observacoes }, cabecalho(chave))).data;
}

export async function entregarVenda(id: number, dados: DadosEntrega, chave: string) {
  return (await api.post<VendaGraos>(`/comercial/vendas/${id}/entregar/`, dados, cabecalho(chave))).data;
}

export async function devolverVenda(id: number, quantidade_kg: string, data_movimento: string, chave: string) {
  return (await api.post<VendaGraos>(`/comercial/vendas/${id}/devolver/`, { quantidade_kg, data_movimento }, cabecalho(chave))).data;
}

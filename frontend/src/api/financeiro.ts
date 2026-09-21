import { api } from "./propriedades";
import axios from "axios";


export type CategoriaFinanceira = {
  id: number;
  nome: string;
  aplicacao: "despesa" | "receita" | "ambos";
  ativa: boolean;
};

export type ParceiroFinanceiro = {
  id: number;
  nome: string;
  tipo: "fornecedor" | "cliente" | "ambos";
  documento: string | null;
  email: string;
  telefone: string;
  ativo: boolean;
};

export type ParceiroFinanceiroInput = {
  nome: string;
  tipo: ParceiroFinanceiro["tipo"];
  documento: string;
  email: string;
  telefone: string;
};

export type FornecedorInput = Omit<ParceiroFinanceiroInput, "tipo">;

export type CentroCusto = {
  id: number;
  nome: string;
  propriedade: number | null;
  propriedade_nome: string | null;
  safra: string;
  ativo: boolean;
};

export type LancamentoFinanceiro = {
  recebedor_nome: string;
  parcela_numero: number | null;
  total_boletos: number | null;
  codigo_barras: string;
  id: number;
  tipo: "pagar" | "receber";
  descricao: string;
  valor: string;
  categoria: number;
  categoria_nome: string | null;
  parceiro: number | null;
  parceiro_nome: string | null;
  centro_custo: number | null;
  centro_custo_nome: string | null;
  propriedade: number | null;
  propriedade_nome: string | null;
  safra: string;
  data_emissao: string;
  data_vencimento: string;
  status: "pendente" | "liquidado" | "cancelado";
  data_liquidacao: string | null;
  valor_liquidado: string | null;
  observacoes: string;
  atrasado: boolean;
};

export type ResumoFinanceiro = {
  a_pagar: string;
  a_receber: string;
  saldo_previsto: string;
  entradas_realizadas: string;
  saidas_realizadas: string;
  saldo_realizado: string;
  valor_atrasado: string;
  quantidade_pendente: number;
};

export type LancamentoInput = {
  codigo_barras?: string;
  tipo: "pagar" | "receber";
  descricao: string;
  valor: string;
  categoria: string;
  parceiro: string;
  centro_custo: string;
  propriedade: string;
  safra: string;
  data_emissao: string;
  data_vencimento: string;
  observacoes: string;
};

export type LeituraCodigoFinanceiro = {
  linha_digitavel?: string;
  linha_digitavel_formatada?: string;
  formato_entrada?: string;
  descricao_sugerida?: string;
  detalhes?: { campo: string; valor: string }[];
  codigo_barras: string;
  tipo: "boleto" | "arrecadacao";
  banco_codigo: string | null;
  banco_nome?: string | null;
  segmento: string | null;
  identificacao_emissor: string | null;
  valor: string | null;
  vencimentos_possiveis: string[];
  avisos: string[];
  lancamentos_existentes: { id: number; descricao: string; status: string }[];
};

export async function lerCodigoFinanceiro(codigo: string): Promise<LeituraCodigoFinanceiro> {
  return (await api.post<LeituraCodigoFinanceiro>("/financeiro/lancamentos/ler-codigo/", { codigo })).data;
}

export async function listarParceirosFinanceiros() {
  return (
    await api.get<ParceiroFinanceiro[]>("/financeiro/parceiros/", {
      params: { ordering: "nome" },
    })
  ).data;
}

export async function listarFornecedores() {
  const parceiros = await listarParceirosFinanceiros();
  return parceiros.filter(
    (item) => item.tipo === "fornecedor" || item.tipo === "ambos",
  );
}

export async function carregarFinanceiro(filtros?: {
  tipo?: string;
  status?: string;
  search?: string;
}) {
  const [categorias, parceiros, centros, lancamentos, resumo] = await Promise.all([
    api.get<CategoriaFinanceira[]>("/financeiro/categorias/"),
    listarParceirosFinanceiros(),
    api.get<CentroCusto[]>("/financeiro/centros-custo/"),
    api.get<LancamentoFinanceiro[]>("/financeiro/lancamentos/", {
      params: { ...filtros, ordering: "data_vencimento" },
    }),
    api.get<ResumoFinanceiro>("/financeiro/lancamentos/resumo/"),
  ]);
  return {
    categorias: categorias.data,
    parceiros,
    centros: centros.data,
    lancamentos: lancamentos.data,
    resumo: resumo.data,
  };
}

export async function criarCategoria(nome: string, aplicacao: string) {
  await api.post("/financeiro/categorias/", { nome, aplicacao, ativa: true });
}

export async function criarParceiro(dados: ParceiroFinanceiroInput) {
  return (
    await api.post<ParceiroFinanceiro>("/financeiro/parceiros/", {
      ...dados,
      ativo: true,
    })
  ).data;
}

export async function criarFornecedor(dados: FornecedorInput) {
  return criarParceiro({ ...dados, tipo: "fornecedor" });
}

export async function atualizarFornecedor(id: number, dados: FornecedorInput) {
  return (await api.patch<ParceiroFinanceiro>(`/financeiro/parceiros/${id}/`, dados)).data;
}

export async function excluirFornecedor(id: number) {
  try {
    await api.delete(`/financeiro/parceiros/${id}/`);
  } catch (falha) {
    if (!axios.isAxiosError(falha) || falha.response?.status !== 409) throw falha;
    await api.patch(`/financeiro/parceiros/${id}/`, { ativo: false });
  }
}

export async function criarCentroCusto(
  nome: string,
  propriedade: string,
  safra: string,
) {
  await api.post("/financeiro/centros-custo/", {
    nome,
    propriedade: propriedade || null,
    safra,
    ativo: true,
  });
}

export async function criarLancamento(dados: LancamentoInput) {
  await api.post("/financeiro/lancamentos/", {
    ...dados,
    categoria: Number(dados.categoria),
    parceiro: dados.parceiro ? Number(dados.parceiro) : null,
    centro_custo: dados.centro_custo ? Number(dados.centro_custo) : null,
    propriedade: dados.propriedade ? Number(dados.propriedade) : null,
  });
}

export type ParcelamentoInput = {
  idempotency_key: string;
  tipo: "pagar" | "receber";
  descricao: string;
  recebedor_nome: string;
  valor_total: string;
  quantidade: number;
  data_emissao: string;
  primeiro_vencimento: string;
  observacoes: string;
  codigo_barras: string;
};

export async function criarParcelamento(dados: ParcelamentoInput) {
  return (await api.post<{ id: string; replay: boolean; parcelas: LancamentoFinanceiro[] }>("/financeiro/lancamentos/parcelar/", dados)).data;
}

export type BoletoCompraInput = Omit<ParcelamentoInput, "quantidade" | "valor_total" | "primeiro_vencimento"> & {
  parcela_numero: number;
  total_boletos: number;
  valor: string;
  data_vencimento: string;
};

export async function registrarBoleto(dados: BoletoCompraInput) {
  return (await api.post<{ boleto: LancamentoFinanceiro; replay: boolean }>("/financeiro/lancamentos/registrar-boleto/", dados)).data;
}

export async function liquidarLancamento(
  id: number,
  dataLiquidacao: string,
  valorLiquidado: string,
) {
  await api.post(`/financeiro/lancamentos/${id}/liquidar/`, {
    data_liquidacao: dataLiquidacao,
    valor_liquidado: valorLiquidado,
  });
}

export async function cancelarLancamento(id: number) {
  await api.post(`/financeiro/lancamentos/${id}/cancelar/`, {});
}

import { api } from "./propriedades";


export type ProdutoEstoque = {
  id: number;
  nome: string;
  categoria: "insumo" | "herbicida" | "fungicida" | "fertilizante" | "semente" | "outro";
  unidade: "kg" | "l" | "un" | "sc" | "t";
  fabricante: string;
  estoque_minimo: string;
  ativo: boolean;
};

export type LocalEstoque = {
  id: number;
  nome: string;
  propriedade: number | null;
  propriedade_nome: string | null;
  descricao: string;
  ativo: boolean;
};

export type LoteEstoque = {
  id: number;
  produto: number;
  produto_nome: string;
  produto_unidade: string;
  local: number;
  local_nome: string;
  codigo: string;
  data_validade: string | null;
  observacoes: string;
  saldo: string;
  vencido: boolean;
  ativo: boolean;
};

export type PosicaoEstoque = {
  lote_id: number;
  produto_id: number;
  produto: string;
  categoria: string;
  unidade: string;
  local_id: number;
  local: string;
  codigo_lote: string;
  data_validade: string | null;
  vencido: boolean;
  vence_em_30_dias: boolean;
  saldo: string;
  abaixo_minimo: boolean;
};

export type MovimentacaoEstoque = {
  id: number;
  tipo: "entrada" | "saida";
  lote: number;
  produto_nome: string;
  unidade: string;
  lote_codigo: string;
  local_nome: string;
  quantidade: string;
  custo_unitario: string | null;
  data_movimento: string;
  documento_fiscal: string;
  propriedade: number | null;
  propriedade_nome: string | null;
  safra: string;
  observacoes: string;
  criado_por_nome: string;
  criado_em: string;
};

export type ResumoEstoque = {
  produtos_ativos: number;
  lotes_com_saldo: number;
  lotes_vencidos: number;
  lotes_vencendo: number;
  itens_abaixo_minimo: number;
};

export async function carregarEstoque(filtros?: {
  search?: string;
  tipo?: string;
  produto?: string;
}) {
  const params = new URLSearchParams();
  if (filtros?.search) params.set("search", filtros.search);
  if (filtros?.tipo) params.set("tipo", filtros.tipo);
  if (filtros?.produto) params.set("produto", filtros.produto);
  const sufixo = params.toString() ? `?${params}` : "";
  const [produtos, locais, lotes, posicoes, movimentos, resumo] = await Promise.all([
    api.get<ProdutoEstoque[]>("/estoque/produtos/?ordering=nome"),
    api.get<LocalEstoque[]>("/estoque/locais/?ordering=nome"),
    api.get<LoteEstoque[]>("/estoque/lotes/?ordering=data_validade"),
    api.get<PosicaoEstoque[]>("/estoque/lotes/posicao/"),
    api.get<MovimentacaoEstoque[]>(`/estoque/movimentacoes/${sufixo}`),
    api.get<ResumoEstoque>("/estoque/lotes/resumo/"),
  ]);
  return {
    produtos: produtos.data,
    locais: locais.data,
    lotes: lotes.data,
    posicoes: posicoes.data,
    movimentos: movimentos.data,
    resumo: resumo.data,
  };
}

export async function criarProduto(dados: {
  nome: string;
  categoria: string;
  unidade: string;
  fabricante: string;
  estoque_minimo: string;
}) {
  return (await api.post<ProdutoEstoque>("/estoque/produtos/", dados)).data;
}

export async function criarLocal(dados: {
  nome: string;
  propriedade: string;
  descricao: string;
}) {
  return (
    await api.post<LocalEstoque>("/estoque/locais/", {
      ...dados,
      propriedade: dados.propriedade || null,
    })
  ).data;
}

export async function criarLote(dados: {
  produto: string;
  local: string;
  codigo: string;
  data_validade: string;
}) {
  return (
    await api.post<LoteEstoque>("/estoque/lotes/", {
      ...dados,
      data_validade: dados.data_validade || null,
    })
  ).data;
}

export async function registrarMovimento(dados: {
  tipo: "entrada" | "saida";
  lote: string;
  quantidade: string;
  custo_unitario: string;
  data_movimento: string;
  documento_fiscal: string;
  propriedade: string;
  safra: string;
  observacoes: string;
}) {
  return (
    await api.post<MovimentacaoEstoque>("/estoque/movimentacoes/", {
      ...dados,
      custo_unitario: dados.custo_unitario || null,
      propriedade: dados.propriedade || null,
    })
  ).data;
}

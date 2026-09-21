import { api } from "./propriedades";
import axios from "axios";


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
  local: number | null;
  local_nome: string;
  fornecedor: number | null;
  fornecedor_nome: string;
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
  local_id: number | null;
  fornecedor_id: number | null;
  fornecedor: string;
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
  fornecedor_nome: string;
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

export type CompraEstoqueInput = {
  safra: string;
  id: string;
  data_compra: string;
  produto: string;
  cultura: string;
  quantidade_embalagens: string;
  embalagem: string;
  conteudo_embalagem: string;
  fornecedor: string;
  custo_embalagem: string;
  data_vencimento: string;
};

export type CompraEstoque = Omit<CompraEstoqueInput, "produto" | "fornecedor" | "data_vencimento"> & {
  data_vencimento: string | null;
  produto_nome: string;
  fornecedor_nome: string;
  unidade: string;
  quantidade_total: string;
  valor_por_unidade: string;
  valor_total: string;
};

export async function listarComprasEstoque(search = "") {
  return (await api.get<CompraEstoque[]>("/estoque/compras/", { params: { search } })).data;
}

export async function registrarCompraEstoque(dados: CompraEstoqueInput) {
  return (await api.post<CompraEstoque>("/estoque/compras/", {
    ...dados, data_vencimento: dados.data_vencimento || null,
  })).data;
}

export type ProdutoEstoqueInput = {
  nome: string;
  categoria: ProdutoEstoque["categoria"];
  unidade: ProdutoEstoque["unidade"];
  fabricante: string;
  estoque_minimo: string;
};

export type LocalEstoqueInput = {
  nome: string;
  propriedade: string;
  descricao: string;
};

export async function listarProdutosEstoque() {
  return (
    await api.get<ProdutoEstoque[]>("/estoque/produtos/", {
      params: { ordering: "nome" },
    })
  ).data;
}

export async function listarLocaisEstoque() {
  return (
    await api.get<LocalEstoque[]>("/estoque/locais/", {
      params: { ordering: "nome" },
    })
  ).data;
}

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
    listarProdutosEstoque(),
    listarLocaisEstoque(),
    api.get<LoteEstoque[]>("/estoque/lotes/?ordering=data_validade"),
    api.get<PosicaoEstoque[]>("/estoque/lotes/posicao/"),
    api.get<MovimentacaoEstoque[]>(`/estoque/movimentacoes/${sufixo}`),
    api.get<ResumoEstoque>("/estoque/lotes/resumo/"),
  ]);
  return {
    produtos,
    locais,
    lotes: lotes.data,
    posicoes: posicoes.data,
    movimentos: movimentos.data,
    resumo: resumo.data,
  };
}

export async function criarProduto(dados: ProdutoEstoqueInput) {
  return (await api.post<ProdutoEstoque>("/estoque/produtos/", dados)).data;
}

export async function criarLocal(dados: LocalEstoqueInput) {
  return (
    await api.post<LocalEstoque>("/estoque/locais/", {
      ...dados,
      propriedade: dados.propriedade || null,
    })
  ).data;
}

export async function atualizarLocal(id: number, dados: LocalEstoqueInput) {
  return (await api.patch<LocalEstoque>(`/estoque/locais/${id}/`, {
    ...dados,
    propriedade: dados.propriedade || null,
  })).data;
}

export async function excluirLocal(id: number) {
  try {
    await api.delete(`/estoque/locais/${id}/`);
  } catch (falha) {
    if (!axios.isAxiosError(falha) || falha.response?.status !== 409) throw falha;
    await api.patch(`/estoque/locais/${id}/`, { ativo: false });
  }
}

export async function atualizarProduto(id: number, dados: ProdutoEstoqueInput) {
  return (await api.patch<ProdutoEstoque>(`/estoque/produtos/${id}/`, dados)).data;
}

export async function excluirProduto(id: number) {
  try {
    await api.delete(`/estoque/produtos/${id}/`);
  } catch (falha) {
    if (!axios.isAxiosError(falha) || falha.response?.status !== 409) throw falha;
    await api.patch(`/estoque/produtos/${id}/`, { ativo: false });
  }
}

export async function criarLote(dados: {
  produto: string;
  fornecedor: string;
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

export type DisponibilidadeEstoque = {
  produto_id: number; produto: string; fornecedor_id: number | null; fornecedor: string;
  unidade: string; data_compra: string | null; quantidade_comprada: string;
  quantidade_saida: string; disponivel: string; valor_aquisicao: string | null;
  preco_medio: string | null; lotes: { id: number; codigo: string; datas_entrada: string[] }[];
};
export async function listarDisponibilidadeEstoque(params: Record<string, string>) {
  return (await api.get<{ itens: DisponibilidadeEstoque[]; resumo: ResumoDisponibilidade[] }>("/estoque/disponibilidade/", { params })).data;
}

export type ResumoDisponibilidade = Pick<DisponibilidadeEstoque, "produto_id" | "produto" | "fornecedor_id" | "fornecedor" | "unidade" | "disponivel" | "preco_medio">;

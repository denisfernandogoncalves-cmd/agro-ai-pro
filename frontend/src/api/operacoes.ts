import { api } from "./propriedades";
import { LoteEstoque } from "./estoque";
import { Pagina, Talhao } from "./talhoes";


export type InsumoOperacao = {
  id: number;
  operacao: number;
  lote: number;
  produto_nome: string;
  lote_codigo: string;
  unidade: string;
  local_nome: string;
  quantidade_planejada: string;
  quantidade_utilizada: string | null;
  movimentacao_estoque: number | null;
};

export type OperacaoAgricola = {
  id: number;
  talhao: number;
  talhao_nome: string;
  propriedade_id: number;
  propriedade_nome: string;
  tipo: string;
  descricao: string;
  data_planejada: string;
  data_inicio: string | null;
  data_conclusao: string | null;
  status: "planejada" | "em_execucao" | "concluida" | "cancelada";
  area_hectares: string;
  responsavel: string;
  custo_estimado: string;
  custo_realizado: string | null;
  observacoes: string;
  criado_por_nome: string;
  insumos: InsumoOperacao[];
};

export type OperacaoInput = {
  talhao: string;
  tipo: string;
  descricao: string;
  data_planejada: string;
  area_hectares: string;
  responsavel: string;
  custo_estimado: string;
  observacoes: string;
};

export async function carregarOperacoes(filtros?: {
  search?: string;
  status?: string;
  tipo?: string;
}) {
  const [operacoes, talhoes, lotes] = await Promise.all([
    api.get<OperacaoAgricola[]>("/producao/operacoes/", { params: filtros }),
    api.get<Pagina<Talhao>>("/talhoes/talhoes/", { params: { page: 1, page_size: 100 } }),
    api.get<LoteEstoque[]>("/estoque/lotes/", { params: { ordering: "data_validade" } }),
  ]);
  return {
    operacoes: operacoes.data,
    talhoes: talhoes.data.results,
    lotes: lotes.data,
  };
}

export async function criarOperacao(dados: OperacaoInput) {
  return (await api.post<OperacaoAgricola>("/producao/operacoes/", dados)).data;
}

export async function adicionarInsumo(dados: {
  operacao: number;
  lote: string;
  quantidade_planejada: string;
  quantidade_utilizada: string;
}) {
  return (
    await api.post<InsumoOperacao>("/producao/insumos/", {
      ...dados,
      quantidade_utilizada: dados.quantidade_utilizada || null,
    })
  ).data;
}

export async function iniciarOperacao(id: number, data_inicio: string) {
  return (
    await api.post<OperacaoAgricola>(`/producao/operacoes/${id}/iniciar/`, {
      data_inicio,
    })
  ).data;
}

export async function concluirOperacao(
  id: number,
  data_conclusao: string,
  custo_realizado: string,
) {
  return (
    await api.post<OperacaoAgricola>(`/producao/operacoes/${id}/concluir/`, {
      data_conclusao,
      custo_realizado: custo_realizado || null,
    })
  ).data;
}

export async function cancelarOperacao(id: number) {
  return (
    await api.post<OperacaoAgricola>(`/producao/operacoes/${id}/cancelar/`)
  ).data;
}

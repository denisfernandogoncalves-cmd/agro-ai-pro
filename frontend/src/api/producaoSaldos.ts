import { api } from "./propriedades";
import { ArmazemGraos, CADPro } from "./cargasColhidas";

export type LoteGraos = {
  id: number;
  codigo: string;
  cad_pro: string;
  cad_pro_codigo: string;
  armazem: number;
  armazem_nome: string;
  propriedade_id: number | null;
  cultura: string;
  safra: string;
  classificacao_codigo: string;
  ativo: boolean;
};

export type FiltrosSaldo = {
  propriedade?: string;
  cad_pro?: string;
  cultura?: string;
  safra?: string;
  classificacao_codigo?: string;
  armazem?: string;
};

export type PosicaoSaldo = {
  id: number;
  cad_pro: string;
  cad_pro_codigo: string;
  cultura: string;
  safra: string;
  classificacao_codigo: string;
  armazem: number;
  armazem_nome: string;
  propriedade_id: number | null;
  propriedade_nome?: string | null;
  saldo_fisico_kg: string;
  saldo_comprometido_kg: string;
  saldo_disponivel_kg: string;
  versao: number;
  atualizado_em: string;
};

export type ConsolidadoCADPro = {
  cad_pro: string;
  cad_pro_codigo: string;
  cad_pro_descricao: string;
  saldo_fisico_kg: string;
  saldo_comprometido_kg: string;
  saldo_disponivel_kg: string;
  posicoes: number;
};

export type PainelSaldos = {
  composicao?: {operacao:string;origem_externa:boolean;fisico_kg:string;comprometido_kg:string}[];
  recebimentos_terceiros?: {posicao:number;quantidade_kg:string}[];
  resumo: {
    propriedades: number;
    cadpros: number;
    posicoes: number;
    saldo_fisico_kg: string;
    saldo_comprometido_kg: string;
    saldo_disponivel_kg: string;
  };
  consolidado_cadpro: ConsolidadoCADPro[];
  consolidado_propriedade: {
    propriedade: number | null;
    propriedade_nome: string;
    cadpros: { id: string; codigo: string }[];
    saldo_fisico_kg: string;
    saldo_comprometido_kg: string;
    saldo_disponivel_kg: string;
    posicoes: number;
  }[];
  posicoes: PosicaoSaldo[];
};

export type MovimentacaoSaldo = {
  posicao?: number;
  origem?: number;
  estornado?: boolean;
  correcao_transferencia?: { acao: "editar" | "excluir"; motivo: string; origem_nova: number | null; criado_em: string; criado_por_nome: string } | null;
  id: number;
  operacao: string;
  lote_codigo: string;
  cad_pro: string;
  cad_pro_codigo: string;
  cultura: string;
  safra: string;
  classificacao_codigo: string;
  armazem_nome: string;
  propriedade_id: number | null;
  quantidade_kg: string;
  delta_fisico_kg: string;
  delta_comprometido_kg: string;
  data_movimento: string;
  referencia_externa: string;
  observacoes: string;
  origem_chave_idempotencia: string;
  criado_por_nome: string;
  criado_em: string;
};

export type CreditoProducaoInput = {
  lote: number;
  quantidade_kg: string;
  data_movimento: string;
  referencia_externa: string;
  observacoes: string;
  chave_idempotencia: string;
};

export async function carregarOpcoesProducaoSaldo() {
  const [cadpros, armazens, lotes] = await Promise.all([
    api.get<CADPro[]>("/cadpros/", { params: { ativo: true } }),
    api.get<ArmazemGraos[]>("/graos/armazens/", { params: { ativo: true } }),
    api.get<LoteGraos[]>("/graos/lotes/", { params: { ativo: true } }),
  ]);
  return { cadpros: cadpros.data, armazens: armazens.data, lotes: lotes.data };
}

export async function consultarPainelSaldos(filtros: FiltrosSaldo = {}) {
  return (
    await api.get<PainelSaldos>("/graos/saldos/painel/", { params: filtros })
  ).data;
}

export async function listarMovimentacoesSaldo(filtros: FiltrosSaldo = {}) {
  return (
    await api.get<MovimentacaoSaldo[]>("/graos/movimentacoes/", {
      params: { ...filtros, ordering: "-data_movimento,-id" },
    })
  ).data;
}

export async function creditarProducao(dados: CreditoProducaoInput) {
  return (
    await api.post("/graos/saldos/creditar-producao/", dados)
  ).data;
}

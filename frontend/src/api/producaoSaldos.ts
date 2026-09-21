import { api } from "./propriedades";
import { ArmazemGraos, CADPro } from "./cargasColhidas";

export type LoteGraos = {
  id: number;
  codigo: string;
  cad_pro: string;
  cad_pro_codigo: string;
  armazem: number;
  armazem_nome: string;
  propriedade_id: number;
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
  propriedade_id: number;
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
  resumo: {
    cadpros: number;
    posicoes: number;
    saldo_fisico_kg: string;
    saldo_comprometido_kg: string;
    saldo_disponivel_kg: string;
  };
  consolidado_cadpro: ConsolidadoCADPro[];
  posicoes: PosicaoSaldo[];
};

export type MovimentacaoSaldo = {
  id: number;
  operacao: string;
  lote_codigo: string;
  cad_pro: string;
  cad_pro_codigo: string;
  cultura: string;
  safra: string;
  classificacao_codigo: string;
  armazem_nome: string;
  quantidade_kg: string;
  delta_fisico_kg: string;
  delta_comprometido_kg: string;
  data_movimento: string;
  referencia_externa: string;
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

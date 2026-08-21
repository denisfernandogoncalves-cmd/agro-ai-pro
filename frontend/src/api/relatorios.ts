import { api } from "./propriedades";

export type SecaoRelatorio = "saldos" | "producao" | "produtividade" | "motoristas" | "reservas" | "vendas" | "entregas" | "movimentacoes" | "rastreabilidade";
export type FiltrosRelatorio = { cad_pro?: string; propriedade?: string; proprietario?: string; cultura?: string; safra?: string; classificacao_codigo?: string; armazem?: string; destinado_semente?: string; motorista?: string; placa?: string; numero_contrato?: string; comprador?: string; data_inicio?: string; data_fim?: string; secao?: SecaoRelatorio; pagina?: number; por_pagina?: number };
export type TotaisOperacionais = { posicoes: number; saldo_fisico_kg: string; saldo_comprometido_kg: string; saldo_disponivel_kg: string; producao_kg: string; producao_rateada_kg: string; semente_kg: string; reservas_abertas_kg: string; vendas_kg: string; entregas_kg: string };
export type PosicaoRelatorio = { id: number; cad_pro: string; cad_pro_codigo: string; cad_pro_descricao: string; propriedade: number; propriedade_nome: string; cultura: string; safra: string; classificacao_codigo: string; armazem: number; armazem_nome: string; saldo_fisico_kg: string; saldo_comprometido_kg: string; saldo_disponivel_kg: string };
export type ItemRelatorio = Record<string, unknown> & { id: number; posicao?: PosicaoRelatorio };
export type RelatorioOperacional = { gerado_em: string; totais: TotaisOperacionais; secao: SecaoRelatorio; por_cad_pro: Array<Record<string, string | number>>; por_propriedade: Array<Record<string, string | number>>; produtividade_por_cad_pro: Array<Record<string, string | number>>; dados: { pagina: number; por_pagina: number; total: number; total_paginas: number; resultados: ItemRelatorio[] } };
export type OpcoesRelatorio = { cadpros: { id: string; codigo: string; descricao: string }[]; proprietarios: string[]; culturas: string[]; safras: string[]; classificacoes: string[]; armazens: { id: number; nome: string; propriedade_id: number; propriedade__nome: string }[]; compradores: string[]; contratos: string[]; motoristas: string[]; placas: string[] };

export async function obterRelatorioOperacional(filtros: FiltrosRelatorio) {
  return (await api.get<RelatorioOperacional>("/relatorios/operacionais/", { params: filtros })).data;
}
export async function obterOpcoesRelatorio() {
  return (await api.get<OpcoesRelatorio>("/relatorios/operacionais/opcoes/")).data;
}

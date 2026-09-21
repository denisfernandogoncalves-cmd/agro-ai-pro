import { api } from "./propriedades";

export type SecaoRelatorio = "saldos" | "producao" | "produtividade" | "producao_propriedade" | "motoristas" | "reservas" | "vendas" | "entregas" | "movimentacoes" | "rastreabilidade" | "estrutura" | "financeiro" | "estoque_insumos" | "operacoes_agricolas" | "maquinas" | "clima" | "mercado" | "importacoes";
export type FiltrosRelatorio = { cad_pro?: string; propriedade?: string; proprietario?: string; cultura?: string; safra?: string; classificacao_codigo?: string; armazem?: string; destinado_semente?: string; motorista?: string; placa?: string; numero_contrato?: string; comprador?: string; data_inicio?: string; data_fim?: string; secao?: SecaoRelatorio; pagina?: number; por_pagina?: number };
export type TotaisOperacionais = { posicoes: number; saldo_fisico_kg: string; saldo_comprometido_kg: string; saldo_disponivel_kg: string; producao_kg: string; producao_rateada_kg: string; semente_kg: string; reservas_abertas_kg: string; vendas_kg: string; entregas_kg: string };
export type PosicaoRelatorio = { id: number; cad_pro: string; cad_pro_codigo: string; cad_pro_descricao: string; propriedade: number; propriedade_nome: string; cultura: string; safra: string; classificacao_codigo: string; armazem: number; armazem_nome: string; saldo_fisico_kg: string; saldo_comprometido_kg: string; saldo_disponivel_kg: string };
export type ItemRelatorio = Record<string, unknown> & { id: string | number; posicao?: PosicaoRelatorio };
export type TotaisProducaoPropriedade = { area_alqueires: string; quantidade_kg: string; sacas_60kg: string; semente_kg: string; semente_sacas_60kg: string; outros_locais_kg: string; media_sacas_alqueire: string };
export type RelatorioOperacional = { gerado_em: string; totais: TotaisOperacionais; totais_producao_propriedade: TotaisProducaoPropriedade; secao: SecaoRelatorio; por_cad_pro: Array<Record<string, string | number>>; por_propriedade: Array<Record<string, string | number>>; produtividade_por_cad_pro: Array<Record<string, string | number>>; dados: { pagina: number; por_pagina: number; total: number; total_paginas: number; resultados: ItemRelatorio[] } };
export type OpcoesRelatorio = { cadpros: { id: string; codigo: string; descricao: string }[]; proprietarios: string[]; culturas: string[]; safras: string[]; classificacoes: string[]; armazens: { id: number; nome: string; propriedade_id: number | null; propriedade__nome: string | null }[]; compradores: string[]; contratos: string[]; motoristas: string[]; placas: string[] };

export async function obterRelatorioOperacional(filtros: FiltrosRelatorio) {
  return (await api.get<RelatorioOperacional>("/relatorios/operacionais/", { params: filtros })).data;
}
export async function obterOpcoesRelatorio() {
  return (await api.get<OpcoesRelatorio>("/relatorios/operacionais/opcoes/")).data;
}

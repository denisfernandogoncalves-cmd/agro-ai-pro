import { api } from "./propriedades";


export type Dashboard = {
  gerado_em: string;
  estrutura: { propriedades: number; talhoes: number; area_talhoes: string };
  financeiro: {
    a_pagar: string; a_receber: string; saldo_previsto: string;
    entradas_realizadas: string; saidas_realizadas: string; saldo_realizado: string;
    valor_atrasado: string; quantidade_pendente: number;
  };
  estoque: {
    produtos_ativos: number; lotes_com_saldo: number; lotes_vencidos: number;
    lotes_vencendo: number; itens_abaixo_minimo: number;
  };
  operacoes: {
    total: number; planejadas: number; em_execucao: number; concluidas: number;
    canceladas: number; custo_estimado: string; custo_realizado: string;
  };
  maquinas: { total: number; ativas: number; em_manutencao: number; manutencoes_pendentes: number };
  fluxo_mensal: { mes: string; entradas: string; saidas: string }[];
};

export async function obterDashboard(propriedade = "", safra = "") {
  return (await api.get<Dashboard>("/relatorios/dashboard/", {
    params: { propriedade: propriedade || undefined, safra: safra || undefined },
  })).data;
}

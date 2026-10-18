import { api } from "./propriedades";
import { OperacaoAgricola } from "./operacoes";


export type Maquina = {
  id: number;
  atualizado_em: string;
  identificacao: string;
  tipo: string;
  marca: string;
  modelo: string;
  ano: number | null;
  propriedade: number | null;
  propriedade_nome: string | null;
  status: "ativa" | "manutencao" | "inativa";
  horimetro_atual: string;
  observacoes: string;
};

export type Manutencao = {
  versao_correcao?: string; horimetro_atual_maquina?:string; versao_maquina_original?:string; data_conclusao?:string|null; horimetro_realizado?:string|null; observacoes?:string;
  id: number;
  maquina: number;
  maquina_nome: string;
  descricao: string;
  data_prevista: string;
  horimetro_previsto: string | null;
  status: "agendada" | "concluida" | "cancelada";
  custo: string;
};

export async function carregarMaquinas() {
  const [maquinas, manutencoes, operacoes, usos, abastecimentos] = await Promise.all([
    api.get<Maquina[]>("/maquinas/maquinas/?ordering=identificacao"),
    api.get<Manutencao[]>("/maquinas/manutencoes/?ordering=data_prevista"),
    api.get<OperacaoAgricola[]>("/producao/operacoes/?ordering=-data_planejada"),
    api.get<HistoricoMaquina[]>("/maquinas/usos/"),
    api.get<HistoricoMaquina[]>("/maquinas/abastecimentos/"),
  ]);
  return {
    maquinas: maquinas.data,
    manutencoes: manutencoes.data,
    operacoes: operacoes.data,
    usos:usos.data, abastecimentos:abastecimentos.data,
  };
}

export async function criarMaquina(dados: Record<string, string>) {
  return (await api.post<Maquina>("/maquinas/maquinas/", {
    ...dados,
    propriedade: dados.propriedade || null,
    ano: dados.ano || null,
  })).data;
}

export async function atualizarMaquina(id: number, dados: Record<string, string>, versao: string) {
  return (await api.patch<Maquina>(`/maquinas/maquinas/${id}/`, { ...dados, propriedade: dados.propriedade || null, ano: dados.ano || null, atualizado_em_original: versao })).data;
}
export const excluirMaquina = async (id: number) => api.delete(`/maquinas/maquinas/${id}/`);
export const excluirManutencao = async (id: number) => api.delete(`/maquinas/manutencoes/${id}/`);
export const editarManutencao = async (id: number, dados: Record<string, string>) => api.patch(`/maquinas/manutencoes/${id}/`, { ...dados, horimetro_previsto: dados.horimetro_previsto || null });

export async function registrarUso(dados: Record<string, string>) {
  await api.post("/maquinas/usos/", dados);
}

export async function registrarAbastecimento(dados: Record<string, string>) {
  await api.post("/maquinas/abastecimentos/", dados);
}

export async function agendarManutencao(dados: Record<string, string>) {
  await api.post("/maquinas/manutencoes/", {
    ...dados,
    horimetro_previsto: dados.horimetro_previsto || null,
  });
}

export async function concluirManutencao(
  id: number,
  dados: Record<string, string>,
) {
  await api.post(`/maquinas/manutencoes/${id}/concluir/`, dados);
}

export type HistoricoMaquina = {id:number; versao_correcao?:string; maquina:number; maquina_nome:string; data:string; operador?:string; operacao_nome?:string; horimetro_inicial?:string; horimetro_final?:string; litros?:string; valor_total?:string; horimetro?:string; documento?:string; observacoes:string; horimetro_atual_maquina:string; versao_maquina_original:string};

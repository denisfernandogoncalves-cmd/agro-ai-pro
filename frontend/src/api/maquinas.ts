import { api } from "./propriedades";
import { OperacaoAgricola } from "./operacoes";


export type Maquina = {
  id: number;
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
  const [maquinas, manutencoes, operacoes] = await Promise.all([
    api.get<Maquina[]>("/maquinas/maquinas/?ordering=identificacao"),
    api.get<Manutencao[]>("/maquinas/manutencoes/?ordering=data_prevista"),
    api.get<OperacaoAgricola[]>("/producao/operacoes/?ordering=-data_planejada"),
  ]);
  return {
    maquinas: maquinas.data,
    manutencoes: manutencoes.data,
    operacoes: operacoes.data,
  };
}

export async function criarMaquina(dados: Record<string, string>) {
  return (await api.post<Maquina>("/maquinas/maquinas/", {
    ...dados,
    propriedade: dados.propriedade || null,
    ano: dados.ano || null,
  })).data;
}

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

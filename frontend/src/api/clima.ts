import { api } from "./propriedades";


export type PrevisaoClima = {
  id: number;
  propriedade: number;
  propriedade_nome: string;
  data: string;
  temperatura_min: string | null;
  temperatura_max: string | null;
  chuva_mm: string | null;
  umidade: number | null;
  vento_kmh: string | null;
  condicao: string;
  probabilidade_chuva: number | null;
  codigo_tempo: number | null;
  alerta_agricola: string;
  fonte: string;
  criado_em: string;
  atualizado_em: string;
};

export async function listarPrevisoes(propriedade: number) {
  const resposta = await api.get<PrevisaoClima[]>("/clima/previsoes/", {
    params: { propriedade, ordering: "data" },
  });
  return resposta.data;
}

export async function atualizarPrevisoes(propriedade: number) {
  const resposta = await api.post<PrevisaoClima[]>(
    "/clima/previsoes/atualizar/",
    { propriedade },
  );
  return resposta.data;
}

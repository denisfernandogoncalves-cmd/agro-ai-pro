import { api } from "./propriedades";


export type PrevisaoClima = {
  id: number;
  propriedade: number;
  propriedade_nome: string;
  data: string;
  temperatura_min: string | null;
  temperatura_max: string | null;
  sensacao_min: string | null;
  sensacao_max: string | null;
  chuva_mm: string | null;
  umidade: number | null;
  vento_kmh: string | null;
  rajada_vento_kmh: string | null;
  direcao_vento: number | null;
  pressao_hpa: string | null;
  cobertura_nuvens: number | null;
  radiacao_solar_mj: string | null;
  ponto_orvalho: string | null;
  evapotranspiracao_mm: string | null;
  nascer_sol: string | null;
  por_sol: string | null;
  condicao: string;
  probabilidade_chuva: number | null;
  codigo_tempo: number | null;
  alerta_agricola: string;
  condicao_pulverizacao: string;
  condicao_colheita: string;
  risco_deriva: boolean;
  risco_lavagem: boolean;
  risco_estresse_hidrico: boolean;
  fonte: string;
  criado_em: string;
  atualizado_em: string;
};

export type PrevisaoHoraria = {
  id: number;
  propriedade: number;
  propriedade_nome: string;
  data_hora: string;
  temperatura: string | null;
  sensacao_termica: string | null;
  umidade: number | null;
  precipitacao_mm: string | null;
  probabilidade_chuva: number | null;
  vento_kmh: string | null;
  direcao_vento: number | null;
  rajada_vento_kmh: string | null;
  pressao_hpa: string | null;
  cobertura_nuvens: number | null;
  radiacao_solar: string | null;
  ponto_orvalho: string | null;
  evapotranspiracao_mm: string | null;
  codigo_tempo: number | null;
  condicao: string;
  condicao_pulverizacao: string;
  condicao_colheita: string;
  risco_deriva: boolean;
  risco_lavagem: boolean;
  fonte: string;
  atualizado_em: string;
};

export type AlertaClimatico = {
  id: number;
  propriedade: number;
  propriedade_nome: string;
  talhao: number | null;
  talhao_nome: string | null;
  tipo: string;
  nivel: "informativo" | "atencao" | "critico";
  titulo: string;
  descricao: string;
  inicio: string;
  fim: string | null;
  ativo: boolean;
  lido_em: string | null;
};

export type ConfiguracaoClima = {
  id: number;
  propriedade: number;
  propriedade_nome: string;
  ativo: boolean;
  frequencia_minutos: number;
  ultima_tentativa: string | null;
  ultima_atualizacao: string | null;
  proxima_atualizacao: string | null;
  status: string;
  erro_ultima_atualizacao: string;
  falhas_consecutivas: number;
  total_chamadas: number;
  origem_coordenadas: string;
  latitude_usada: string | null;
  longitude_usada: string | null;
  altitude_usada: string | null;
  dados_atuais: Record<string, string | number>;
  desatualizado: boolean;
};

export type StatusClima = {
  configuracao: ConfiguracaoClima;
  atual: Record<string, string | number>;
  proxima_hora: PrevisaoHoraria | null;
  alertas_ativos: number;
};

function hojeEmSaoPaulo() {
  const partes = new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Sao_Paulo",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date());
  const valores = Object.fromEntries(
    partes.filter((parte) => parte.type !== "literal").map((parte) => [parte.type, parte.value]),
  );
  return `${valores.year}-${valores.month}-${valores.day}`;
}

export async function listarPrevisoes(propriedade: number) {
  const resposta = await api.get<PrevisaoClima[]>("/clima/previsoes/", {
    params: { propriedade, ordering: "data" },
  });
  const hoje = hojeEmSaoPaulo();
  return resposta.data.filter((item) => item.data >= hoje).slice(0, 7);
}

export async function listarPrevisoesHorarias(propriedade: number) {
  const resposta = await api.get<PrevisaoHoraria[]>("/clima/horarias/", {
    params: { propriedade, ordering: "data_hora" },
  });
  return resposta.data;
}

export async function listarAlertasClimaticos(propriedade: number) {
  const resposta = await api.get<AlertaClimatico[]>("/clima/alertas/", {
    params: { propriedade, ativo: true, ordering: "-inicio" },
  });
  return resposta.data;
}

export async function obterStatusClima(propriedade: number) {
  const resposta = await api.get<StatusClima>("/clima/previsoes/status/", {
    params: { propriedade },
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

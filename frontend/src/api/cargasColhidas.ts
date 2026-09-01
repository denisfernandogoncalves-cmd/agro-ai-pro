import { api, Propriedade } from "./propriedades";
import { Talhao } from "./talhoes";


export type CADPro = {
  id: string;
  codigo: string;
  descricao: string;
  ativo: boolean;
  propriedades: number[];
};

export type ArmazemGraos = {
  id: number;
  propriedade: number | null;
  propriedade_nome: string | null;
  nome: string;
  capacidade_kg: string;
  ocupacao_kg: string;
  ativo: boolean;
};

export type CargaColhida = {
  id: number;
  propriedade: number;
  propriedade_nome: string;
  cad_pro: string;
  cad_pro_codigo: string;
  cultura: string;
  safra: string;
  armazem: number;
  armazem_nome: string;
  lote: number;
  lote_codigo: string;
  data_colheita: string;
  placa: string;
  motorista: string;
  peso_bruto_kg: string;
  umidade_percentual: string;
  impureza_percentual: string;
  defeitos_percentual: string;
  ph: string | null;
  destinado_semente: boolean;
  local_colheita: string;
  desconto_total_percentual: string;
  desconto_total_kg: string;
  peso_liquido_kg: string;
  sacas_60kg: string;
  regra_desconto_aplicada: Record<string, unknown>;
  contexto_colheita: Record<string, unknown>;
  movimentacao: number;
  observacoes: string;
  criado_por_nome: string;
  criado_em: string;
  status: "ativa" | "cancelada" | "substituida";
  cancelada_em: string | null;
  cancelada_por_nome: string | null;
  motivo_cancelamento: string;
  substituida_por: number | null;
};

export type CargaColhidaInput = {
  chave_registro?: string;
  propriedade: string;
  cad_pro: string;
  cultura: string;
  safra: string;
  armazem: string;
  data_colheita: string;
  placa: string;
  motorista: string;
  peso_bruto_kg: string;
  umidade_percentual: string;
  impureza_percentual: string;
  defeitos_percentual: string;
  ph: string;
  destinado_semente: boolean;
  local_colheita: string;
  observacoes: string;
  talhoes_selecionados: number[];
  propriedades_selecionadas: number[];
  cadpros_por_propriedade: Record<string, string>;
  tolerancia_impureza_percentual?: string;
  desconto_impureza_por_ponto?: string;
  tolerancia_defeitos_percentual?: string;
  desconto_defeitos_por_ponto?: string;
  ph_minimo?: string;
  desconto_ph_por_ponto?: string;
  motivo_correcao?: string;
};

export async function carregarContextoCargas(propriedades: Propriedade[]) {
  const [armazens, cadpros, cargas, talhoes] = await Promise.all([
    api.get<ArmazemGraos[]>("/graos/armazens/"),
    api.get<CADPro[]>("/cadpros/"),
    api.get<CargaColhida[]>("/graos/cargas-colhidas/", {
      params: { ordering: "-data_colheita" },
    }),
    api.get<Talhao[]>("/talhoes/talhoes/"),
  ]);
  return {
    propriedades,
    armazens: armazens.data,
    cadpros: cadpros.data,
    cargas: cargas.data,
    talhoes: talhoes.data,
  };
}

function montarPayloadCarga(dados: CargaColhidaInput) {
  return {
    ...dados,
    propriedade: Number(dados.propriedade),
    armazem: Number(dados.armazem),
    ph: dados.ph || null,
    tolerancia_impureza_percentual:
      dados.tolerancia_impureza_percentual || undefined,
    desconto_impureza_por_ponto:
      dados.desconto_impureza_por_ponto || undefined,
    tolerancia_defeitos_percentual:
      dados.tolerancia_defeitos_percentual || undefined,
    desconto_defeitos_por_ponto:
      dados.desconto_defeitos_por_ponto || undefined,
    ph_minimo: dados.ph_minimo || undefined,
    desconto_ph_por_ponto: dados.desconto_ph_por_ponto || undefined,
  };
}

export async function criarCargaColhida(dados: CargaColhidaInput) {
  return (await api.post<CargaColhida>(
    "/graos/cargas-colhidas/",
    montarPayloadCarga(dados),
  )).data;
}

export async function atualizarCargaColhida(
  id: number,
  dados: CargaColhidaInput,
) {
  return (await api.patch<CargaColhida>(
    `/graos/cargas-colhidas/${id}/`,
    montarPayloadCarga(dados),
  )).data;
}

export async function excluirCargaColhida(id: number, motivo: string) {
  await api.delete(`/graos/cargas-colhidas/${id}/`, { data: { motivo } });
}

import { api, Propriedade } from "./propriedades";


export type CADPro = {
  id: string;
  codigo: string;
  descricao: string;
  ativo: boolean;
};

export type ArmazemGraos = {
  id: number;
  propriedade: number;
  propriedade_nome: string;
  nome: string;
  capacidade_kg: string;
  ocupacao_kg: string;
  ativo: boolean;
};

export type GrupoColheita = {
  id: number;
  propriedade: number;
  propriedade_nome: string;
  cad_pro: string;
  cad_pro_codigo: string;
  nome: string;
  cultura: string;
  safra: string;
  tolerancia_umidade_percentual: string;
  desconto_umidade_por_ponto: string;
  tolerancia_impureza_percentual: string;
  desconto_impureza_por_ponto: string;
  tolerancia_defeitos_percentual: string;
  desconto_defeitos_por_ponto: string;
  ativo: boolean;
};

export type CargaColhida = {
  id: number;
  propriedade: number;
  propriedade_nome: string;
  grupo_colheita: number;
  grupo_colheita_nome: string;
  cad_pro: string;
  cad_pro_codigo: string;
  armazem: number;
  armazem_nome: string;
  lote: number;
  lote_codigo: string;
  data_colheita: string;
  placa: string;
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
  movimentacao: number;
  observacoes: string;
  criado_por_nome: string;
  criado_em: string;
};

export type GrupoColheitaInput = Omit<
  GrupoColheita,
  "id" | "propriedade_nome" | "cad_pro_codigo" | "ativo"
>;

export type CargaColhidaInput = {
  grupo_colheita: string;
  armazem: string;
  data_colheita: string;
  placa: string;
  peso_bruto_kg: string;
  umidade_percentual: string;
  impureza_percentual: string;
  defeitos_percentual: string;
  ph: string;
  destinado_semente: boolean;
  local_colheita: string;
  observacoes: string;
};

export async function carregarContextoCargas(propriedades: Propriedade[]) {
  const [cadpros, armazens, grupos, cargas] = await Promise.all([
    api.get<CADPro[]>("/cadpros/", { params: { ativo: true } }),
    api.get<ArmazemGraos[]>("/graos/armazens/", { params: { ativo: true } }),
    api.get<GrupoColheita[]>("/graos/grupos-colheita/", { params: { ativo: true } }),
    api.get<CargaColhida[]>("/graos/cargas-colhidas/", {
      params: { ordering: "-data_colheita" },
    }),
  ]);
  return {
    propriedades,
    cadpros: cadpros.data,
    armazens: armazens.data,
    grupos: grupos.data,
    cargas: cargas.data,
  };
}

export async function criarGrupoColheita(dados: GrupoColheitaInput) {
  return (await api.post<GrupoColheita>("/graos/grupos-colheita/", dados)).data;
}

export async function criarCargaColhida(dados: CargaColhidaInput) {
  return (await api.post<CargaColhida>("/graos/cargas-colhidas/", {
    ...dados,
    ph: dados.ph || null,
  })).data;
}

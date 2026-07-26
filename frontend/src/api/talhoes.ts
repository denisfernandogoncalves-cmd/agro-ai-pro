import { api } from "./propriedades";
import { GeometriaGeoJSON } from "../utils/geometria";

export type GeometriaTalhao = GeometriaGeoJSON;

export type Talhao = {
  id: number;
  propriedade: number;
  propriedade_nome: string;
  nome: string;
  area_hectares: string;
  arquivo_kml: string | null;
  latitude_centro: string | null;
  longitude_centro: string | null;
  geometria_geojson: GeometriaTalhao | null;
  area_calculada_hectares: string | null;
  diferenca_area_hectares: string | null;
  divergencia_area_percentual: string | null;
  cultura_atual: string;
  safra: string;
  tipo_solo: string;
  altitude_media: string | null;
  declividade_media: string | null;
  produtividade_esperada: string | null;
  produtividade_realizada: string | null;
  observacoes: string;
  criado_em: string;
  atualizado_em: string;
};

export type TalhaoInput = {
  propriedade: string;
  nome: string;
  area_hectares: string;
  cultura_atual: string;
  safra: string;
  tipo_solo: string;
  altitude_media: string;
  declividade_media: string;
  produtividade_esperada: string;
  produtividade_realizada: string;
  observacoes: string;
  arquivo_kml: File | null;
};

export type HistoricoAgronomico = {
  id: number;
  talhao: number;
  talhao_nome: string;
  data_referencia: string;
  cultura: string;
  safra: string;
  produtividade_esperada: string | null;
  produtividade_realizada: string | null;
  observacoes: string;
  criado_em: string;
  atualizado_em: string;
};

export type HistoricoAgronomicoInput = {
  talhao: number;
  data_referencia: string;
  cultura: string;
  safra: string;
  produtividade_esperada: string;
  produtividade_realizada: string;
  observacoes: string;
};

export type Pagina<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

export type FiltrosTalhao = {
  search?: string;
  propriedade?: string;
  cultura?: string;
  safra?: string;
  ordering?: string;
  page?: number;
  pageSize?: number;
};

function montarFormulario(dados: TalhaoInput) {
  const formulario = new FormData();
  Object.entries(dados).forEach(([campo, valor]) => {
    if (valor !== null && valor !== "") {
      formulario.append(campo, valor);
    }
  });
  return formulario;
}

export async function listarTalhoes(filtros: FiltrosTalhao = {}) {
  const response = await api.get<Pagina<Talhao>>("/talhoes/talhoes/", {
    params: {
      search: filtros.search || undefined,
      propriedade: filtros.propriedade || undefined,
      cultura: filtros.cultura || undefined,
      safra: filtros.safra || undefined,
      ordering: filtros.ordering || undefined,
      page: filtros.page || 1,
      page_size: filtros.pageSize || 10,
    },
  });
  return response.data;
}

export async function criarTalhao(dados: TalhaoInput) {
  const response = await api.post<Talhao>(
    "/talhoes/talhoes/",
    montarFormulario(dados),
  );
  return response.data;
}

export async function atualizarTalhao(id: number, dados: TalhaoInput) {
  const response = await api.patch<Talhao>(
    `/talhoes/talhoes/${id}/`,
    montarFormulario(dados),
  );
  return response.data;
}

export async function excluirTalhao(id: number) {
  await api.delete(`/talhoes/talhoes/${id}/`);
}

export async function listarHistoricos(talhao: number) {
  const response = await api.get<Pagina<HistoricoAgronomico>>(
    "/talhoes/historicos-agronomicos/",
    { params: { talhao, ordering: "-data_referencia", page_size: 100 } },
  );
  return response.data.results;
}

export async function criarHistorico(dados: HistoricoAgronomicoInput) {
  const response = await api.post<HistoricoAgronomico>(
    "/talhoes/historicos-agronomicos/",
    dados,
  );
  return response.data;
}

export async function atualizarHistorico(
  id: number,
  dados: HistoricoAgronomicoInput,
) {
  const response = await api.patch<HistoricoAgronomico>(
    `/talhoes/historicos-agronomicos/${id}/`,
    dados,
  );
  return response.data;
}

export async function excluirHistorico(id: number) {
  await api.delete(`/talhoes/historicos-agronomicos/${id}/`);
}

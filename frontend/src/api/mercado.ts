import { api } from "./propriedades";


export type ProdutoMercado = "soja" | "milho" | "trigo" | "brent";

export type CotacaoMercado = {
  id: number;
  produto: ProdutoMercado;
  produto_nome: string;
  data: string;
  valor: string;
  unidade: string;
  fonte: string;
};

export type ResumoMercado = {
  produto: ProdutoMercado;
  produto_nome: string;
  data: string;
  valor: string;
  unidade: string;
  variacao_percentual: string | null;
  tendencia: string;
  aviso: string;
};

export type ClimaCornBelt = {
  id: number;
  regiao: string;
  regiao_nome: string;
  data: string;
  temperatura_min: string;
  temperatura_max: string;
  precipitacao_mm: string;
  alerta: string;
  fonte: string;
};

export type NoticiaMercado = {
  id: number;
  titulo: string;
  resumo: string;
  fonte: string;
  url: string;
  publicada_em: string;
  ativa: boolean;
};

export async function carregarPainelMercado() {
  const [cotacoes, resumos, clima, noticias] = await Promise.all([
    api.get<CotacaoMercado[]>("/mercado/cotacoes/", {
      params: { ordering: "produto,data" },
    }),
    api.get<ResumoMercado[]>("/mercado/cotacoes/resumo/"),
    api.get<ClimaCornBelt[]>("/mercado/corn-belt/", {
      params: { ordering: "regiao,data" },
    }),
    api.get<NoticiaMercado[]>("/mercado/noticias/", {
      params: { ativa: true, ordering: "-publicada_em" },
    }),
  ]);
  return {
    cotacoes: cotacoes.data,
    resumos: resumos.data,
    clima: clima.data,
    noticias: noticias.data,
  };
}

export async function atualizarCotacoes() {
  await api.post("/mercado/cotacoes/atualizar/", {});
}

export async function atualizarCornBelt() {
  await api.post("/mercado/corn-belt/atualizar/", {});
}

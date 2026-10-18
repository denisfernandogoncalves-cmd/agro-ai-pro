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
  atualizado_em?: string;
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
  atualizado_em?: string;
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


export type CotacaoCBOT = {
  id:number;
  produto:"soja"|"milho"|"trigo";
  produto_nome:string;
  simbolo:string;
  contrato:string;
  contrato_completo:boolean;
  cotado_em:string;
  valor_usd_bushel:string;
  valor_centavos_bushel:string;
  fonte:string;
  unidade:string;
  aviso:string;
  criado_em:string;
};

export async function listarCBOT() {
  return (await api.get<CotacaoCBOT[]>("/mercado/cbot/")).data;
}
export async function atualizarCBOT() {
  return (await api.post<CotacaoCBOT[]>("/mercado/cbot/atualizar/",{})).data;
}


export type ReferenciaInvesting = {
  produto:string; nome:string; simbolo?:string; contrato?:string; fonte?:string; url?:string;
  valor?:string; valor_original?:string; unidade?:string; cotado_em?:string;
  consultado_em?:string; derivado?:boolean; atraso_provedor?:boolean; mercado_aberto?:boolean; erro:string;
};
export async function consultarInvesting() {
  return (await api.get<{cotacoes:ReferenciaInvesting[];intervalo_segundos:number;aviso:string}>("/mercado/investing/", {timeout:20000})).data;
}

export async function consultarReferenciasMercado() {
  return (await api.get<{cotacoes:ReferenciaInvesting[];intervalo_segundos:number;aviso:string}>("/mercado/referencias/", {timeout:20000})).data;
}

import { api } from "./propriedades";


export type ProdutoMercado = "soja" | "milho" | "trigo" | "brent";
export type AtivoMercado =
  | "soja_cbot"
  | "milho_cbot"
  | "trigo_cbot"
  | "farelo_soja"
  | "oleo_soja"
  | "brent"
  | "dolar";
export type JanelaMercado = "intraday" | "5d" | "30d";

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

export type PontoMercadoEnterprise = {
  id: number;
  ativo: AtivoMercado;
  ativo_nome: string;
  intervalo: "snapshot" | "diario";
  data_hora: string;
  abertura: string | null;
  maxima: string | null;
  minima: string | null;
  fechamento: string;
  volume: string | null;
  unidade: string;
  moeda: string;
  fonte: string;
  simbolo_origem: string;
};

export type ResumoAtivoEnterprise = {
  ativo: AtivoMercado;
  ativo_nome: string;
  disponivel: boolean;
  cotacao_atual?: string;
  abertura?: string | null;
  maxima?: string | null;
  minima?: string | null;
  variacao_diaria?: string | null;
  data_hora?: string;
  unidade?: string;
  moeda?: string;
  fonte?: string;
  status: string;
  ultima_atualizacao?: string | null;
  proxima_atualizacao?: string | null;
  desatualizado?: boolean;
  mensagem?: string;
};

export type AnaliseMercadoEnterprise = {
  gerado_em: string;
  impactos: Array<{ fator: string; direcao: "alta" | "baixa"; descricao: string }>;
  fatores_alta: string[];
  fatores_baixa: string[];
  tendencia_curto_prazo: "alta" | "baixa" | "mista";
  recomendacao_operacional: string;
  contexto_producao: {
    estoque_kg?: string;
    contratado_aberto_kg?: string;
    saldo_conjunto_kg?: string;
  };
  corn_belt: {
    chuva_media: string | null;
    temperatura_minima: string | null;
    temperatura_maxima: string | null;
    alertas: string[];
  };
  aviso: string;
};

export type PainelMercadoEnterprise = {
  ativos: ResumoAtivoEnterprise[];
  analise: AnaliseMercadoEnterprise;
  atualizacoes: Array<{
    ativo: AtivoMercado;
    status: string;
    ultima_atualizacao: string | null;
    proxima_atualizacao: string | null;
    mensagem_erro: string;
    total_chamadas: number;
  }>;
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

export async function carregarPainelMercadoEnterprise(propertyId?: number | null) {
  return (await api.get<PainelMercadoEnterprise>("/mercado/cotacoes-enterprise/painel/", {
    params: { propriedade: propertyId || undefined },
  })).data;
}

export async function carregarSerieMercado(ativo: AtivoMercado, janela: JanelaMercado) {
  return (await api.get<PontoMercadoEnterprise[]>("/mercado/cotacoes-enterprise/serie/", {
    params: { ativo, janela },
  })).data;
}

export async function atualizarMercadoEnterprise(ativo?: AtivoMercado) {
  return (await api.post("/mercado/cotacoes-enterprise/atualizar/", ativo ? { ativo } : {})).data;
}

export async function atualizarCotacoes() {
  await api.post("/mercado/cotacoes/atualizar/", {});
}

export async function atualizarCornBelt() {
  await api.post("/mercado/corn-belt/atualizar/", {});
}

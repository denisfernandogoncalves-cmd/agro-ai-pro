import { api } from "./propriedades";

export type ListResponse<T> = T[] | { results: T[]; count?: number };

export type SafraProducao = {
  id: number;
  nome: string;
  data_inicio: string | null;
  data_fim: string | null;
  ativa: boolean;
};

export type CulturaProducao = {
  id: number;
  nome: string;
  codigo: string;
  peso_saca_kg: string;
  ativa: boolean;
};

export type CadPro = {
  id: number;
  propriedade: number;
  propriedade_nome: string;
  codigo: string;
  titular: string;
  documento: string;
  inscricao_estadual: string;
  ativo: boolean;
};

export type TalhaoResumo = {
  id: number;
  propriedade: number;
  propriedade_nome: string;
  nome: string;
  area_hectares: string;
  cultura_atual: string;
  safra: string;
  latitude_centro: string | null;
  longitude_centro: string | null;
  geometria_geojson: unknown | null;
};

export type LocalArmazenagem = {
  id: number;
  nome: string;
  propriedade: number | null;
  propriedade_nome?: string;
};

export type DetalheLocalArmazenagem = {
  id: number;
  local: number;
  local_nome: string;
  propriedade: number | null;
  propriedade_nome: string | null;
  tipo: "silo" | "armazem" | "cooperativa" | "terceiro" | "outro";
  capacidade_kg: string | null;
  latitude: string | null;
  longitude: string | null;
  ativo: boolean;
};

export type Parceiro = {
  id: number;
  nome: string;
  tipo: "fornecedor" | "cliente" | "ambos";
  documento: string;
  ativo: boolean;
};

export type Motorista = {
  id: number;
  nome: string;
  documento: string | null;
  telefone: string;
  ativo: boolean;
};

export type Veiculo = {
  id: number;
  placa: string;
  tipo: string;
  descricao: string;
  ativo: boolean;
};

export type ContratoProducao = {
  id: number;
  propriedade: number;
  propriedade_nome: string;
  cadpro: number;
  cadpro_codigo: string;
  cultura: number;
  cultura_nome: string;
  safra: number;
  safra_nome: string;
  comprador: number;
  comprador_nome: string;
  numero: string;
  data_contrato: string;
  data_limite: string | null;
  quantidade_kg: string;
  preco_saca: string;
  tolerancia_percentual: string;
  status: "aberto" | "concluido" | "cancelado";
};

export type RecebimentoProducao = {
  id: number;
  data: string;
  propriedade: number;
  propriedade_nome: string;
  cadpro: number;
  cadpro_codigo: string;
  talhao: number | null;
  talhao_nome: string | null;
  cultura: number;
  cultura_nome: string;
  safra: number;
  safra_nome: string;
  local_armazenagem: number;
  local_armazenagem_nome: string;
  motorista: number | null;
  motorista_nome: string | null;
  veiculo: number | null;
  veiculo_placa: string | null;
  placa_informada: string;
  romaneio: string;
  peso_bruto_kg: string;
  tara_kg: string;
  peso_liquido_kg: string;
  quantidade_sacas: string;
  umidade_percentual: string;
  impureza_percentual: string;
  defeitos_percentual: string;
  status: "rascunho" | "confirmado" | "estornado";
  terceiro_id?: number | null;
  terceiro_nome?: string | null;
};

export type SaldoGraos = {
  id: number;
  propriedade: number;
  propriedade_nome: string;
  cadpro: number;
  cadpro_codigo: string;
  talhao: number | null;
  talhao_nome: string | null;
  cultura: number;
  cultura_nome: string;
  safra: number;
  safra_nome: string;
  local_armazenagem: number;
  local_armazenagem_nome: string;
  quantidade_kg: string;
  quantidade_sacas: string;
  toneladas: string;
  atualizado_em: string;
};

export type EmbarqueProducao = {
  id: number;
  data: string;
  propriedade: number;
  propriedade_nome: string;
  cadpro: number;
  cadpro_codigo: string;
  cultura: number;
  cultura_nome: string;
  safra: number;
  safra_nome: string;
  local_armazenagem: number;
  local_armazenagem_nome: string;
  comprador: number;
  comprador_nome: string;
  contrato: number | null;
  contrato_numero: string | null;
  destino: string;
  romaneio: string;
  nota_produtor: string;
  nota_empresa: string;
  quantidade_kg: string;
  quantidade_sacas: string;
  preco_saca: string;
  valor_total: string;
  status: "rascunho" | "confirmado" | "estornado";
};

export type TransferenciaGraos = {
  id: number;
  data: string;
  propriedade_origem: number;
  propriedade_origem_nome: string;
  cadpro_origem: number;
  cadpro_origem_codigo: string;
  local_origem: number;
  local_origem_nome: string;
  propriedade_destino: number;
  propriedade_destino_nome: string;
  cadpro_destino: number;
  cadpro_destino_codigo: string;
  local_destino: number;
  local_destino_nome: string;
  cultura: number;
  cultura_nome: string;
  safra: number;
  safra_nome: string;
  quantidade_kg: string;
  status: "rascunho" | "confirmada" | "estornada";
  motivo: string;
};

export type ImportacaoProducao = {
  id: number;
  tipo: "recebimentos" | "embarques";
  nome_original: string;
  status: "enviada" | "validada" | "importada" | "erro";
  total_linhas: number;
  linhas_importadas: number;
  previa: Record<string, unknown>[];
  inconsistencias: string[];
  criado_em: string;
};

export type DashboardProducao = {
  producao: { peso_liquido_kg: string; sacas: string; cargas: number };
  produtividade: {
    media_sacas_hectare: string | null;
    melhor_talhao: { talhao_nome: string; sacas_hectare: string } | null;
    menor_talhao: { talhao_nome: string; sacas_hectare: string } | null;
    por_talhao: Array<{ talhao_id: number; talhao_nome: string; area_hectares: string; peso_kg: string; sacas: string; sacas_hectare: string }>;
  };
  qualidade: {
    umidade_media: string | null;
    impureza_media: string | null;
    defeitos_media: string | null;
    alertas: Array<{ recebimento_id: number; cultura: string; umidade_percentual: string; limite_percentual: string }>;
  };
  estoque: {
    disponivel_kg: string;
    posicoes: number;
    alertas_minimo: Array<{ cultura_id: number; cultura: string; quantidade_kg: string; minimo_kg: string }>;
    capacidade_mapeada_kg: string | null;
  };
  embarques: { quantidade_kg: string; valor_total: string; total: number };
  contratos: { abertos: number; alertas_limite: Array<{ contrato_id: number; numero: string; saldo_kg: string; percentual_restante: string }> };
  saldo_disponivel_kg: string;
  receita: string;
  por_propriedade: Array<{ propriedade_id: number; propriedade__nome: string; peso_kg: string; sacas: string }>;
  por_cadpro: Array<{ cadpro_id: number; cadpro__codigo: string; peso_kg: string; sacas: string }>;
};

export type ProducaoBundle = {
  dashboard: DashboardProducao;
  safras: SafraProducao[];
  culturas: CulturaProducao[];
  cadpros: CadPro[];
  talhoes: TalhaoResumo[];
  locais: LocalArmazenagem[];
  detalhesLocais: DetalheLocalArmazenagem[];
  parceiros: Parceiro[];
  motoristas: Motorista[];
  veiculos: Veiculo[];
  contratos: ContratoProducao[];
  recebimentos: RecebimentoProducao[];
  saldos: SaldoGraos[];
  embarques: EmbarqueProducao[];
  transferencias: TransferenciaGraos[];
  importacoes: ImportacaoProducao[];
  safraSelecionadaId: number | null;
};

export function normalizarLista<T>(data: ListResponse<T>): T[] {
  return Array.isArray(data) ? data : data.results;
}

function contextoParams(propriedadeId?: number | null, safraId?: number | null) {
  return {
    propriedade: propriedadeId || undefined,
    safra: safraId || undefined,
  };
}

export async function carregarGestaoProducao({
  propriedadeId,
  safraNome,
}: {
  propriedadeId?: number | null;
  safraNome?: string;
}): Promise<ProducaoBundle> {
  const [safrasResponse, culturasResponse, cadprosResponse, locaisResponse, parceirosResponse, motoristasResponse, veiculosResponse, talhoesResponse] = await Promise.all([
    api.get<ListResponse<SafraProducao>>("/producao/safras/", { params: { ordering: "-nome" } }),
    api.get<ListResponse<CulturaProducao>>("/producao/culturas/", { params: { ordering: "nome" } }),
    api.get<ListResponse<CadPro>>("/producao/cadpros/", { params: { propriedade: propriedadeId || undefined, ordering: "codigo" } }),
    api.get<ListResponse<LocalArmazenagem>>("/estoque/locais/", { params: { propriedade: propriedadeId || undefined, ordering: "nome" } }),
    api.get<ListResponse<Parceiro>>("/financeiro/parceiros/", { params: { ordering: "nome" } }),
    api.get<ListResponse<Motorista>>("/producao/motoristas/", { params: { ordering: "nome" } }),
    api.get<ListResponse<Veiculo>>("/producao/veiculos/", { params: { ordering: "placa" } }),
    api.get<ListResponse<TalhaoResumo>>("/talhoes/talhoes/", { params: { propriedade: propriedadeId || undefined, page_size: 250, ordering: "nome" } }),
  ]);

  const safras = normalizarLista(safrasResponse.data);
  const culturas = normalizarLista(culturasResponse.data);
  const cadpros = normalizarLista(cadprosResponse.data);
  const locais = normalizarLista(locaisResponse.data);
  const parceiros = normalizarLista(parceirosResponse.data);
  const motoristas = normalizarLista(motoristasResponse.data);
  const veiculos = normalizarLista(veiculosResponse.data);
  const talhoes = normalizarLista(talhoesResponse.data);
  const safraSelecionadaId = safras.find((item) => item.nome === safraNome)?.id ?? null;
  const params = contextoParams(propriedadeId, safraSelecionadaId);

  const [dashboardResponse, detalhesLocaisResponse, contratosResponse, recebimentosResponse, saldosResponse, embarquesResponse, transferenciasResponse, importacoesResponse] = await Promise.all([
    api.get<DashboardProducao>("/producao/dashboard-integrado/", { params }),
    api.get<ListResponse<DetalheLocalArmazenagem>>("/producao/locais-armazenagem/", { params: { propriedade: propriedadeId || undefined, ordering: "local__nome" } }),
    api.get<ListResponse<ContratoProducao>>("/producao/contratos/", { params: { ...params, ordering: "-data_contrato" } }),
    api.get<ListResponse<RecebimentoProducao>>("/producao/recebimentos/", { params: { ...params, ordering: "-data" } }),
    api.get<ListResponse<SaldoGraos>>("/producao/saldos-graos/", { params: { ...params, ordering: "-quantidade_kg" } }),
    api.get<ListResponse<EmbarqueProducao>>("/producao/embarques/", { params: { ...params, ordering: "-data" } }),
    api.get<ListResponse<TransferenciaGraos>>("/producao/transferencias/", { params: { ordering: "-data" } }),
    api.get<ListResponse<ImportacaoProducao>>("/producao/importacoes/", { params: { ordering: "-criado_em" } }),
  ]);

  return {
    dashboard: dashboardResponse.data,
    safras,
    culturas,
    cadpros,
    talhoes,
    locais,
    detalhesLocais: normalizarLista(detalhesLocaisResponse.data),
    parceiros,
    motoristas,
    veiculos,
    contratos: normalizarLista(contratosResponse.data),
    recebimentos: normalizarLista(recebimentosResponse.data),
    saldos: normalizarLista(saldosResponse.data),
    embarques: normalizarLista(embarquesResponse.data),
    transferencias: normalizarLista(transferenciasResponse.data),
    importacoes: normalizarLista(importacoesResponse.data),
    safraSelecionadaId,
  };
}

export async function criarRecebimento(payload: Record<string, unknown>) {
  return (await api.post<RecebimentoProducao>("/producao/recebimentos/", payload)).data;
}

export async function confirmarRecebimento(id: number) {
  return (await api.post<RecebimentoProducao>(`/producao/recebimentos/${id}/confirmar/`, {})).data;
}

export async function criarContrato(payload: Record<string, unknown>) {
  return (await api.post<ContratoProducao>("/producao/contratos/", payload)).data;
}

export async function criarEmbarque(payload: Record<string, unknown>) {
  return (await api.post<EmbarqueProducao>("/producao/embarques/", payload)).data;
}

export async function confirmarEmbarque(id: number) {
  return (await api.post<EmbarqueProducao>(`/producao/embarques/${id}/confirmar/`, {})).data;
}

export async function criarTransferencia(payload: Record<string, unknown>) {
  return (await api.post<TransferenciaGraos>("/producao/transferencias/", payload)).data;
}

export async function confirmarTransferencia(id: number) {
  return (await api.post<TransferenciaGraos>(`/producao/transferencias/${id}/confirmar/`, {})).data;
}

export async function enviarPlanilha({
  arquivo,
  tipo,
  propriedade,
  cadpro,
  mapeamento,
}: {
  arquivo: File;
  tipo: "recebimentos" | "embarques";
  propriedade: number;
  cadpro?: number | null;
  mapeamento?: Record<string, string>;
}) {
  const form = new FormData();
  form.append("arquivo", arquivo);
  form.append("tipo", tipo);
  form.append("propriedade", String(propriedade));
  if (cadpro) form.append("cadpro", String(cadpro));
  if (mapeamento) form.append("mapeamento", JSON.stringify(mapeamento));
  return (await api.post<ImportacaoProducao>("/producao/importacoes/", form)).data;
}

export async function confirmarImportacao(id: number) {
  return (await api.post<ImportacaoProducao>(`/producao/importacoes/${id}/confirmar/`, {})).data;
}

export async function baixarRelatorioProducao({
  tipo,
  formato,
  propriedade,
  safra,
  cadpro,
}: {
  tipo: "recebimentos" | "embarques" | "contratos" | "estoque";
  formato: "csv" | "xlsx" | "pdf";
  propriedade?: number | null;
  safra?: number | null;
  cadpro?: number | null;
}) {
  const response = await api.get<Blob>("/producao/relatorios-integrados/", {
    params: {
      tipo,
      formato,
      propriedade: propriedade || undefined,
      safra: safra || undefined,
      cadpro: cadpro || undefined,
    },
    responseType: "blob",
  });
  const url = URL.createObjectURL(response.data);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `producao-${tipo}.${formato}`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

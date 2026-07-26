import { api } from "./propriedades";

export type OptionRecord = { id: number; nome: string };
export type CadPro = { id: number; propriedade: number; propriedade_nome: string; codigo: string; titular: string; ativo: boolean };
export type CulturaProducao = { id: number; nome: string; codigo: string; peso_saca_kg: string; ativa: boolean };
export type SafraProducao = { id: number; nome: string; ativa: boolean };
export type LocalArmazenagem = { id: number; nome: string; propriedade: number | null };
export type Comprador = { id: number; nome: string; tipo: string };
export type TalhaoResumo = { id: number; nome: string; propriedade: number; safra: string };

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
  local_nome: string;
  motorista_nome: string | null;
  placa: string;
  romaneio: string;
  peso_bruto_kg: string;
  tara_kg: string;
  peso_liquido_kg: string;
  quantidade_sacas: string;
  umidade_percentual: string;
  impureza_percentual: string;
  defeitos_percentual: string;
  status: "rascunho" | "confirmado" | "estornado";
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
  local_nome: string;
  quantidade_kg: string;
  quantidade_sacas: string;
  atualizado_em: string;
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
  quantidade_embarcada_kg: string;
  saldo_contrato_kg: string;
  preco_saca: string;
  status: "aberto" | "concluido" | "cancelado";
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
  local_nome: string;
  comprador: number;
  comprador_nome: string;
  contrato: number | null;
  contrato_numero: string | null;
  romaneio: string;
  placa: string;
  quantidade_kg: string;
  quantidade_sacas: string;
  preco_saca: string;
  valor_total: string;
  status: "rascunho" | "confirmado" | "estornado";
};

export type ImportacaoProducao = {
  id: number;
  tipo: "recebimentos" | "movimentacoes" | "embarques";
  nome_original: string;
  status: "enviada" | "validada" | "importada" | "erro";
  total_linhas: number;
  linhas_importadas: number;
  mapeamento: Record<string, string>;
  previa: Array<Record<string, unknown>>;
  inconsistencias: Array<{ linha: number; campo?: string; mensagem: string }>;
};

export type DashboardProducao = {
  producao: { peso_liquido_kg: string; sacas: string; cargas: number };
  qualidade: { umidade_media: string | null; impureza_media: string | null; defeitos_media: string | null };
  estoque: { disponivel_kg: string; posicoes: number };
  embarques: { quantidade_kg: string; valor_total: string; total: number };
  contratos: { abertos: number };
  por_propriedade: Array<{ propriedade_id: number; propriedade__nome: string; peso_kg: string; sacas: string }>;
  por_cadpro: Array<{ cadpro_id: number; cadpro__codigo: string; peso_kg: string; sacas: string }>;
  por_talhao: Array<{ talhao_id: number; talhao__nome: string; peso_kg: string; sacas: string }>;
};

type ListResponse<T> = T[] | { results: T[] };
const rows = <T,>(data: ListResponse<T>) => Array.isArray(data) ? data : data.results;

const contextParams = (propertyId?: number | null, harvestId?: string) => ({
  propriedade: propertyId || undefined,
  safra: harvestId || undefined,
});

export async function carregarCadastrosProducao(propertyId?: number | null) {
  const [cadpros, culturas, safras, locais, compradores, talhoes] = await Promise.all([
    api.get<ListResponse<CadPro>>("/producao/cadpros/", { params: { propriedade: propertyId || undefined } }),
    api.get<ListResponse<CulturaProducao>>("/producao/culturas/", { params: { ordering: "nome" } }),
    api.get<ListResponse<SafraProducao>>("/producao/safras/", { params: { ordering: "-nome" } }),
    api.get<ListResponse<LocalArmazenagem>>("/estoque/locais/", { params: { propriedade: propertyId || undefined } }),
    api.get<ListResponse<Comprador>>("/financeiro/parceiros/", { params: { ordering: "nome" } }),
    api.get<ListResponse<TalhaoResumo>>("/talhoes/talhoes/", { params: { propriedade: propertyId || undefined, page_size: 200 } }),
  ]);
  return {
    cadpros: rows(cadpros.data),
    culturas: rows(culturas.data),
    safras: rows(safras.data),
    locais: rows(locais.data),
    compradores: rows(compradores.data).filter((item) => item.tipo === "cliente" || item.tipo === "ambos"),
    talhoes: rows(talhoes.data),
  };
}

export async function carregarPainelProducao(propertyId?: number | null, harvestId = "") {
  const params = contextParams(propertyId, harvestId);
  const [dashboard, recebimentos, saldos, contratos, embarques, importacoes] = await Promise.all([
    api.get<DashboardProducao>("/producao/dashboard-integrado/", { params }),
    api.get<ListResponse<RecebimentoProducao>>("/producao/recebimentos/", { params: { ...params, ordering: "-data" } }),
    api.get<ListResponse<SaldoGraos>>("/producao/saldos-graos/", { params: { ...params, ordering: "-quantidade_kg" } }),
    api.get<ListResponse<ContratoProducao>>("/producao/contratos/", { params: { ...params, ordering: "-data_contrato" } }),
    api.get<ListResponse<EmbarqueProducao>>("/producao/embarques/", { params: { ...params, ordering: "-data" } }),
    api.get<ListResponse<ImportacaoProducao>>("/producao/importacoes/", { params: { propriedade: propertyId || undefined } }),
  ]);
  return {
    dashboard: dashboard.data,
    recebimentos: rows(recebimentos.data),
    saldos: rows(saldos.data),
    contratos: rows(contratos.data),
    embarques: rows(embarques.data),
    importacoes: rows(importacoes.data),
  };
}

export type RecebimentoInput = {
  propriedade: number;
  cadpro: number;
  talhao: number | null;
  cultura: number;
  safra: number;
  local_armazenagem: number;
  data?: string;
  placa_informada?: string;
  romaneio?: string;
  peso_bruto_kg: string;
  tara_kg: string;
  peso_liquido_kg: string;
  umidade_percentual: string;
  impureza_percentual: string;
  defeitos_percentual: string;
};

export async function criarRecebimento(data: RecebimentoInput) {
  return (await api.post<RecebimentoProducao>("/producao/recebimentos/", data)).data;
}

export async function confirmarRecebimento(id: number) {
  return (await api.post<RecebimentoProducao>(`/producao/recebimentos/${id}/confirmar/`, {})).data;
}

export type ContratoInput = {
  propriedade: number;
  cadpro: number;
  cultura: number;
  safra: number;
  comprador: number;
  numero: string;
  data_contrato: string;
  data_limite?: string | null;
  quantidade_kg: string;
  preco_saca: string;
  tolerancia_percentual: string;
};

export async function criarContrato(data: ContratoInput) {
  return (await api.post<ContratoProducao>("/producao/contratos/", data)).data;
}

export type EmbarqueInput = {
  propriedade: number;
  cadpro: number;
  cultura: number;
  safra: number;
  local_armazenagem: number;
  comprador: number;
  contrato: number | null;
  data?: string;
  romaneio: string;
  placa_informada?: string;
  destino?: string;
  nota_produtor?: string;
  nota_empresa?: string;
  quantidade_kg: string;
  preco_saca: string;
};

export async function criarEmbarque(data: EmbarqueInput) {
  return (await api.post<EmbarqueProducao>("/producao/embarques/", data)).data;
}

export async function confirmarEmbarque(id: number) {
  return (await api.post<EmbarqueProducao>(`/producao/embarques/${id}/confirmar/`, {})).data;
}

export async function enviarImportacao(params: {
  tipo: ImportacaoProducao["tipo"];
  propriedade: number;
  cadpro: number;
  arquivo: File;
}) {
  const form = new FormData();
  form.append("tipo", params.tipo);
  form.append("propriedade", String(params.propriedade));
  form.append("cadpro", String(params.cadpro));
  form.append("arquivo", params.arquivo);
  return (await api.post<ImportacaoProducao>("/producao/importacoes/", form)).data;
}

export async function confirmarImportacao(id: number) {
  return (await api.post<ImportacaoProducao>(`/producao/importacoes/${id}/confirmar/`, {})).data;
}

export async function baixarRelatorioProducao(
  formato: "csv" | "xlsx" | "pdf",
  propertyId?: number | null,
  harvestId = "",
) {
  const response = await api.get(`/producao/relatorios-integrados/`, {
    params: { ...contextParams(propertyId, harvestId), formato },
    responseType: "blob",
  });
  const href = URL.createObjectURL(response.data);
  const anchor = document.createElement("a");
  anchor.href = href;
  anchor.download = `producao.${formato}`;
  anchor.click();
  URL.revokeObjectURL(href);
}

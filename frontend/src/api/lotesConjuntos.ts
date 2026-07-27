import { api } from "./propriedades";
import type {
  CadPro,
  CulturaProducao,
  LocalArmazenagem,
  SafraProducao,
  TalhaoResumo,
} from "./producaoIntegrada";

export type MetodoRateio = "sem_rateio" | "area" | "manual";
export type StatusLoteConjunto = "rascunho" | "conferencia" | "confirmado" | "encerrado" | "estornado";

export type TalhaoParticipante = {
  id?: number;
  talhao: number;
  talhao_nome?: string;
  area_cadastrada_ha: string;
  area_colhida_ha: string;
  observacoes?: string;
};

export type ParticipanteLoteConjunto = {
  id?: number;
  propriedade: number;
  propriedade_nome?: string;
  municipio?: string;
  produtor?: string;
  cadpro: number | null;
  cadpro_codigo?: string | null;
  area_cadastrada_ha: string;
  area_colhida_ha: string;
  percentual_area?: string;
  quantidade_rateada_kg?: string | null;
  metodo_rateio?: "nao_rateado" | "area" | "manual";
  justificativa_excesso_area?: string;
  justificativa_rateio?: string;
  observacoes?: string;
  talhoes: TalhaoParticipante[];
};

export type CargaLoteConjunto = {
  id: number;
  lote: number;
  data_hora: string;
  motorista: number | null;
  motorista_nome: string | null;
  veiculo_cavalo: number | null;
  veiculo_carreta: number | null;
  placa_cavalo_informada: string;
  placa_carreta_informada: string;
  placa_cavalo: string;
  placa_carreta: string;
  transportadora: number | null;
  transportadora_nome: string | null;
  origem: string;
  destino: string;
  peso_bruto_kg: string;
  tara_kg: string;
  peso_liquido_kg: string;
  quantidade_sacas: string;
  umidade_percentual: string;
  impureza_percentual: string;
  defeitos_percentual: string;
  romaneio: string;
  numero_balanca: string;
  nota_fiscal: string;
  local_armazenagem: number;
  local_nome: string;
  observacoes: string;
};

export type SaldoConjunto = {
  id: number;
  local_armazenagem: number;
  local_nome: string;
  quantidade_kg: string;
};

export type CadProDistribuido = {
  id: number;
  participante: number | null;
  cadpro: number;
  cadpro_codigo: string;
  propriedade_nome: string;
  quantidade_atribuida_kg: string;
  metodo_rateio: "nao_rateado" | "area" | "manual";
  justificativa: string;
};

export type LoteConjunto = {
  id: number;
  codigo: string;
  descricao: string;
  cultura: number;
  cultura_nome: string;
  variedade: string;
  safra: number;
  safra_nome: string;
  data_inicio_colheita: string;
  data_final_colheita: string | null;
  cadpro_responsavel: number | null;
  cadpro_responsavel_codigo: string | null;
  local_armazenagem: number;
  local_nome: string;
  modo_rateio: MetodoRateio;
  area_total_cadastrada_ha: string;
  area_total_colhida_ha: string;
  peso_bruto_total_kg: string;
  tara_total_kg: string;
  peso_liquido_total_kg: string;
  quantidade_toneladas: string;
  quantidade_sacas: string;
  produtividade_kg_ha: string;
  produtividade_sacas_ha: string;
  umidade_media: string;
  impureza_media: string;
  defeitos_medios: string;
  quantidade_cargas: number;
  observacoes: string;
  status: StatusLoteConjunto;
  participantes: ParticipanteLoteConjunto[];
  cargas: CargaLoteConjunto[];
  cadpros_participantes: CadProDistribuido[];
  saldos_conjuntos: SaldoConjunto[];
  criado_em: string;
  atualizado_em: string;
  confirmado_em: string | null;
};

export type LoteConjuntoInput = {
  descricao?: string;
  cultura: number;
  variedade?: string;
  safra: number;
  data_inicio_colheita: string;
  data_final_colheita?: string | null;
  cadpro_responsavel?: number | null;
  local_armazenagem: number;
  modo_rateio: MetodoRateio;
  observacoes?: string;
  participantes: ParticipanteLoteConjunto[];
};

export type MotoristaResumo = { id: number; nome: string; documento?: string | null };
export type VeiculoResumo = { id: number; placa: string; tipo: string; descricao?: string };
export type ParceiroResumo = { id: number; nome: string; tipo: string };

export type CadastrosLoteConjunto = {
  culturas: CulturaProducao[];
  safras: SafraProducao[];
  cadpros: CadPro[];
  locais: LocalArmazenagem[];
  talhoes: TalhaoResumo[];
  motoristas: MotoristaResumo[];
  veiculos: VeiculoResumo[];
  parceiros: ParceiroResumo[];
};

type ListResponse<T> = T[] | { results: T[] };
const rows = <T,>(data: ListResponse<T>) => Array.isArray(data) ? data : data.results;

export async function carregarCadastrosLoteConjunto(): Promise<CadastrosLoteConjunto> {
  const [culturas, safras, cadpros, locais, talhoes, motoristas, veiculos, parceiros] = await Promise.all([
    api.get<ListResponse<CulturaProducao>>("/producao/culturas/", { params: { ordering: "nome" } }),
    api.get<ListResponse<SafraProducao>>("/producao/safras/", { params: { ordering: "-nome" } }),
    api.get<ListResponse<CadPro>>("/producao/cadpros/", { params: { page_size: 500 } }),
    api.get<ListResponse<LocalArmazenagem>>("/estoque/locais/", { params: { page_size: 500 } }),
    api.get<ListResponse<TalhaoResumo>>("/talhoes/talhoes/", { params: { page_size: 500 } }),
    api.get<ListResponse<MotoristaResumo>>("/producao/motoristas/", { params: { ordering: "nome", page_size: 500 } }),
    api.get<ListResponse<VeiculoResumo>>("/producao/veiculos/", { params: { ordering: "placa", page_size: 500 } }),
    api.get<ListResponse<ParceiroResumo>>("/financeiro/parceiros/", { params: { ordering: "nome", page_size: 500 } }),
  ]);
  return {
    culturas: rows(culturas.data),
    safras: rows(safras.data),
    cadpros: rows(cadpros.data),
    locais: rows(locais.data),
    talhoes: rows(talhoes.data),
    motoristas: rows(motoristas.data),
    veiculos: rows(veiculos.data),
    parceiros: rows(parceiros.data),
  };
}

export async function listarLotesConjuntos(params: Record<string, string | number | undefined> = {}) {
  const response = await api.get<ListResponse<LoteConjunto>>("/producao/lotes-conjuntos/", { params });
  return rows(response.data);
}

export async function obterLoteConjunto(id: number) {
  return (await api.get<LoteConjunto>(`/producao/lotes-conjuntos/${id}/`)).data;
}

export async function criarLoteConjunto(data: LoteConjuntoInput) {
  return (await api.post<LoteConjunto>("/producao/lotes-conjuntos/", data)).data;
}

export async function atualizarLoteConjunto(id: number, data: Partial<LoteConjuntoInput>) {
  return (await api.patch<LoteConjunto>(`/producao/lotes-conjuntos/${id}/`, data)).data;
}

export async function adicionarCargaLote(data: Omit<CargaLoteConjunto, "id" | "motorista_nome" | "placa_cavalo" | "placa_carreta" | "transportadora_nome" | "local_nome" | "quantidade_sacas">) {
  return (await api.post<CargaLoteConjunto>("/producao/cargas-lotes-conjuntos/", data)).data;
}

export async function colocarLoteEmConferencia(id: number) {
  return (await api.post<LoteConjunto>(`/producao/lotes-conjuntos/${id}/colocar-em-conferencia/`, {})).data;
}

export async function confirmarLoteConjunto(id: number) {
  return (await api.post<LoteConjunto>(`/producao/lotes-conjuntos/${id}/confirmar/`, {})).data;
}

export async function ratearLotePorArea(id: number) {
  return (await api.post<LoteConjunto>(`/producao/lotes-conjuntos/${id}/ratear-area/`, {})).data;
}

export async function ratearLoteManual(id: number, itens: Array<{ participante: number; cadpro: number; quantidade: string; unidade: "kg" | "toneladas" | "sacas" }>, justificativa: string, distribuirTodoSaldo = true) {
  return (await api.post<LoteConjunto>(`/producao/lotes-conjuntos/${id}/ratear-manual/`, {
    itens,
    justificativa,
    distribuir_todo_saldo: distribuirTodoSaldo,
  })).data;
}

export async function criarSaidaLoteConjunto(data: {
  lote: number;
  local_armazenagem: number;
  comprador?: number | null;
  contrato?: number | null;
  motorista?: number | null;
  veiculo_cavalo?: number | null;
  veiculo_carreta?: number | null;
  placa_cavalo_informada?: string;
  placa_carreta_informada?: string;
  destino?: string;
  romaneio: string;
  nota_produtor?: string;
  nota_empresa?: string;
  quantidade_kg: string;
  justificativa?: string;
}) {
  return (await api.post<{ id: number }>("/producao/saidas-lotes-conjuntos/", data)).data;
}

export async function confirmarSaidaLoteConjunto(id: number) {
  return (await api.post(`/producao/saidas-lotes-conjuntos/${id}/confirmar/`, {})).data;
}

export async function transferirSaldoLote(id: number, localOrigem: number, localDestino: number, quantidadeKg: string) {
  return (await api.post(`/producao/lotes-conjuntos/${id}/transferir/`, {
    local_origem: localOrigem,
    local_destino: localDestino,
    quantidade_kg: quantidadeKg,
  })).data;
}

export async function baixarRelatorioLotesConjuntos(formato: "csv" | "xlsx" | "pdf", params: Record<string, string | number | undefined> = {}) {
  const response = await api.get("/producao/relatorios-lotes-conjuntos/", {
    params: { ...params, formato },
    responseType: "blob",
  });
  const href = URL.createObjectURL(response.data);
  const link = document.createElement("a");
  link.href = href;
  link.download = `lotes-conjuntos.${formato}`;
  link.click();
  URL.revokeObjectURL(href);
}

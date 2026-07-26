import { api } from "./propriedades";

export type CulturaProducao = {
  id: number;
  nome: string;
  codigo: string;
  peso_saca_kg: string;
  ativa: boolean;
};

export type SafraProducao = {
  id: number;
  nome: string;
  data_inicio: string | null;
  data_fim: string | null;
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

export type LocalArmazenagem = {
  id: number;
  nome: string;
  propriedade: number | null;
  descricao: string;
  ativo: boolean;
};

export type Parceiro = {
  id: number;
  nome: string;
  tipo: "fornecedor" | "cliente" | "ambos";
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
  local_nome: string;
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
  preco_saca: string;
  tolerancia_percentual: string;
  quantidade_embarcada_kg: string;
  saldo_contrato_kg: string;
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

export type DashboardProducao = {
  producao: { peso_liquido_kg: string; sacas: string; cargas: number };
  qualidade: {
    umidade_media: string | null;
    impureza_media: string | null;
    defeitos_media: string | null;
  };
  estoque: { disponivel_kg: string; posicoes: number };
  embarques: { quantidade_kg: string; valor_total: string; total: number };
  contratos: { abertos: number };
  por_propriedade: Array<{ propriedade_id: number; propriedade__nome: string; peso_kg: string; sacas: string }>;
  por_cadpro: Array<{ cadpro_id: number; cadpro__codigo: string; peso_kg: string; sacas: string }>;
  por_talhao: Array<{
    talhao_id: number;
    talhao__nome: string;
    talhao__area_hectares: string;
    peso_kg: string;
    sacas: string;
    produtividade_sacas_ha: string | null;
  }>;
};

export type ImportacaoPlanilha = {
  id: number;
  tipo: "recebimentos" | "movimentacoes" | "embarques";
  propriedade: number;
  propriedade_nome: string;
  cadpro: number | null;
  cadpro_codigo: string | null;
  nome_original: string;
  mapeamento: Record<string, string>;
  previa: Array<Record<string, unknown>>;
  inconsistencias: Array<{ linha: number; campo?: string; mensagem: string }>;
  total_linhas: number;
  linhas_importadas: number;
  status: "enviada" | "validada" | "importada" | "erro";
};

export type RecebimentoInput = {
  propriedade: number;
  cadpro: number;
  cultura: number;
  safra: number;
  local_armazenagem: number;
  romaneio: string;
  peso_bruto_kg: string;
  tara_kg: string;
  peso_liquido_kg: string;
  umidade_percentual: string;
  impureza_percentual: string;
  defeitos_percentual: string;
};

export type ContratoInput = {
  propriedade: number;
  cadpro: number;
  cultura: number;
  safra: number;
  comprador: number;
  numero: string;
  data_contrato: string;
  data_limite: string | null;
  quantidade_kg: string;
  preco_saca: string;
  tolerancia_percentual: string;
};

export type EmbarqueInput = {
  propriedade: number;
  cadpro: number;
  cultura: number;
  safra: number;
  local_armazenagem: number;
  comprador: number;
  contrato: number | null;
  destino: string;
  romaneio: string;
  nota_produtor: string;
  nota_empresa: string;
  quantidade_kg: string;
  preco_saca: string;
};

function params(propertyId = "", safraId = "") {
  return {
    propriedade: propertyId || undefined,
    safra: safraId || undefined,
  };
}

export async function carregarProducaoIntegrada(propertyId = "", safraId = "") {
  const filterParams = params(propertyId, safraId);
  const [
    dashboard,
    cadpros,
    culturas,
    safras,
    locais,
    parceiros,
    recebimentos,
    saldos,
    contratos,
    embarques,
    importacoes,
  ] = await Promise.all([
    api.get<DashboardProducao>("/producao/dashboard-integrado/", { params: filterParams }),
    api.get<CadPro[]>("/producao/cadpros/", { params: { propriedade: propertyId || undefined } }),
    api.get<CulturaProducao[]>("/producao/culturas/"),
    api.get<SafraProducao[]>("/producao/safras/"),
    api.get<LocalArmazenagem[]>("/estoque/locais/", { params: { propriedade: propertyId || undefined } }),
    api.get<Parceiro[]>("/financeiro/parceiros/"),
    api.get<RecebimentoProducao[]>("/producao/recebimentos/", { params: filterParams }),
    api.get<SaldoGraos[]>("/producao/saldos-graos/", { params: filterParams }),
    api.get<ContratoProducao[]>("/producao/contratos/", { params: filterParams }),
    api.get<EmbarqueProducao[]>("/producao/embarques/", { params: filterParams }),
    api.get<ImportacaoPlanilha[]>("/producao/importacoes/", { params: { propriedade: propertyId || undefined } }),
  ]);
  return {
    dashboard: dashboard.data,
    cadpros: cadpros.data,
    culturas: culturas.data,
    safras: safras.data,
    locais: locais.data,
    parceiros: parceiros.data.filter((item) => item.tipo !== "fornecedor"),
    recebimentos: recebimentos.data,
    saldos: saldos.data,
    contratos: contratos.data,
    embarques: embarques.data,
    importacoes: importacoes.data,
  };
}

export async function criarRecebimento(input: RecebimentoInput) {
  return (await api.post<RecebimentoProducao>("/producao/recebimentos/", input)).data;
}

export async function confirmarRecebimento(id: number) {
  return (await api.post<RecebimentoProducao>(`/producao/recebimentos/${id}/confirmar/`, {})).data;
}

export async function criarContrato(input: ContratoInput) {
  return (await api.post<ContratoProducao>("/producao/contratos/", input)).data;
}

export async function criarEmbarque(input: EmbarqueInput) {
  return (await api.post<EmbarqueProducao>("/producao/embarques/", input)).data;
}

export async function confirmarEmbarque(id: number) {
  return (await api.post<EmbarqueProducao>(`/producao/embarques/${id}/confirmar/`, {})).data;
}

export async function enviarImportacao(input: {
  arquivo: File;
  tipo: ImportacaoPlanilha["tipo"];
  propriedade: number;
  cadpro?: number;
}) {
  const data = new FormData();
  data.append("arquivo", input.arquivo);
  data.append("tipo", input.tipo);
  data.append("propriedade", String(input.propriedade));
  if (input.cadpro) data.append("cadpro", String(input.cadpro));
  return (await api.post<ImportacaoPlanilha>("/producao/importacoes/", data)).data;
}

export async function confirmarImportacao(id: number) {
  return (await api.post<ImportacaoPlanilha>(`/producao/importacoes/${id}/confirmar/`, {})).data;
}

export async function baixarRelatorio(
  formato: "csv" | "xlsx" | "pdf",
  propertyId = "",
  safraId = "",
  type: "recebimentos" | "embarques" | "estoque" | "contratos" = "recebimentos",
) {
  const response = await api.get<Blob>("/producao/relatorios-integrados/", {
    params: { ...params(propertyId, safraId), formato, tipo: type },
    responseType: "blob",
  });
  const url = URL.createObjectURL(response.data);
  const link = document.createElement("a");
  link.href = url;
  link.download = `producao-${type}.${formato}`;
  link.click();
  URL.revokeObjectURL(url);
}

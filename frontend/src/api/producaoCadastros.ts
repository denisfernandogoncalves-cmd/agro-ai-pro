import { api } from "./propriedades";
import type {
  CadPro,
  CulturaProducao,
  DetalheLocalArmazenagem,
  Motorista,
  SafraProducao,
  Veiculo,
} from "./producaoIntegrada";

export async function criarCadPro(payload: {
  propriedade: number;
  codigo: string;
  titular: string;
  documento?: string;
  inscricao_estadual?: string;
}) {
  return (await api.post<CadPro>("/producao/cadpros/", payload)).data;
}

export async function criarCultura(payload: {
  nome: string;
  codigo: string;
  peso_saca_kg: string;
}) {
  return (await api.post<CulturaProducao>("/producao/culturas/", payload)).data;
}

export async function criarSafra(payload: {
  nome: string;
  data_inicio?: string;
  data_fim?: string;
}) {
  return (await api.post<SafraProducao>("/producao/safras/", payload)).data;
}

export async function criarMotorista(payload: {
  nome: string;
  documento?: string;
  telefone?: string;
}) {
  return (await api.post<Motorista>("/producao/motoristas/", payload)).data;
}

export async function criarVeiculo(payload: {
  placa: string;
  tipo: string;
  descricao?: string;
  motorista_padrao?: number | null;
}) {
  return (await api.post<Veiculo>("/producao/veiculos/", payload)).data;
}

export async function criarDetalheLocal(payload: {
  local: number;
  tipo: DetalheLocalArmazenagem["tipo"];
  capacidade_kg?: string;
  latitude?: string;
  longitude?: string;
}) {
  return (
    await api.post<DetalheLocalArmazenagem>(
      "/producao/locais-armazenagem/",
      payload,
    )
  ).data;
}

import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";
import { GeometriaGeoJSON } from "../utils/geometria";


export type PapelPropriedade =
  | "administrador"
  | "gestor"
  | "operador"
  | "leitura";

export type Propriedade = {
  id: number;
  nome: string;
  proprietario: string;
  municipio: string;
  uf: string;
  area_hectares: string;
  latitude: string | null;
  longitude: string | null;
  arquivo_kml: string | null;
  geometria_geojson: GeometriaGeoJSON | null;
  area_calculada_hectares: string | null;
  diferenca_area_hectares: string | null;
  divergencia_area_percentual: string | null;
  observacoes: string;
  criado_em: string;
  papel_usuario: PapelPropriedade | null;
  pode_editar: boolean;
  pode_excluir: boolean;
  pode_operar: boolean;
};

export type PermissoesUsuario = {
  pode_criar_propriedade: boolean;
  superusuario: boolean;
};

export type PropriedadeInput = {
  nome: string;
  proprietario: string;
  municipio: string;
  uf: string;
  area_hectares: string;
  latitude: string;
  longitude: string;
  observacoes: string;
  arquivo_kml: File | null;
};

const TOKEN_KEY = "agro-ai-pro.access-token";
const REFRESH_TOKEN_KEY = "agro-ai-pro.refresh-token";
const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000/api";

type RequisicaoComRetry = InternalAxiosRequestConfig & {
  _retry?: boolean;
};

export const api = axios.create({
  baseURL: API_URL,
});

const apiSemAutenticacao = axios.create({
  baseURL: API_URL,
});

let renovacaoEmAndamento: Promise<string> | null = null;

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

async function renovarAccessToken() {
  const refresh = localStorage.getItem(REFRESH_TOKEN_KEY);
  if (!refresh) {
    throw new Error("Refresh token não disponível.");
  }
  const response = await apiSemAutenticacao.post<{ access: string }>(
    "/auth/token/refresh/",
    { refresh },
  );
  localStorage.setItem(TOKEN_KEY, response.data.access);
  return response.data.access;
}

api.interceptors.response.use(
  (response) => response,
  async (erro: AxiosError) => {
    const requisicao = erro.config as RequisicaoComRetry | undefined;
    const endpointAutenticacao = requisicao?.url?.includes("/auth/token/");
    if (
      erro.response?.status !== 401
      || !requisicao
      || requisicao._retry
      || endpointAutenticacao
    ) {
      return Promise.reject(erro);
    }

    requisicao._retry = true;
    try {
      if (!renovacaoEmAndamento) {
        renovacaoEmAndamento = renovarAccessToken().finally(() => {
          renovacaoEmAndamento = null;
        });
      }
      const token = await renovacaoEmAndamento;
      requisicao.headers.Authorization = `Bearer ${token}`;
      return api.request(requisicao);
    } catch (erroRenovacao) {
      sair();
      if (typeof window !== "undefined") {
        window.location.reload();
      }
      return Promise.reject(erroRenovacao);
    }
  },
);

export function estaAutenticado() {
  return Boolean(
    localStorage.getItem(TOKEN_KEY)
    && localStorage.getItem(REFRESH_TOKEN_KEY),
  );
}

export async function autenticar(username: string, password: string) {
  const response = await apiSemAutenticacao.post<{
    access: string;
    refresh: string;
  }>("/auth/token/", {
    username,
    password,
  });
  localStorage.setItem(TOKEN_KEY, response.data.access);
  localStorage.setItem(REFRESH_TOKEN_KEY, response.data.refresh);
}

function aplicarPermissoesNaInterface(propriedades: Propriedade[]) {
  if (typeof document === "undefined") {
    return;
  }
  const papeis = new Set(propriedades.map((item) => item.papel_usuario));
  const podeGerenciar = papeis.has("administrador") || papeis.has("gestor");
  const podeOperar = podeGerenciar || papeis.has("operador");
  document.body.dataset.podeGerenciar = String(podeGerenciar);
  document.body.dataset.podeOperar = String(podeOperar);
}

export function sair() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  if (typeof document !== "undefined") {
    delete document.body.dataset.podeGerenciar;
    delete document.body.dataset.podeOperar;
  }
}

export async function listarPropriedades(search = "") {
  const response = await api.get<Propriedade[]>("/propriedades/", {
    params: search ? { search } : undefined,
  });
  if (!search) {
    aplicarPermissoesNaInterface(response.data);
  }
  return response.data;
}

export async function obterPermissoesUsuario() {
  const response = await api.get<PermissoesUsuario>(
    "/propriedades/permissoes/",
  );
  return response.data;
}

function montarFormulario(dados: PropriedadeInput) {
  const formulario = new FormData();
  Object.entries(dados).forEach(([campo, valor]) => {
    if (valor !== null && valor !== "") {
      formulario.append(campo, valor);
    }
  });
  return formulario;
}

export async function criarPropriedade(dados: PropriedadeInput) {
  const response = await api.post<Propriedade>(
    "/propriedades/",
    montarFormulario(dados),
  );
  return response.data;
}

export async function atualizarPropriedade(id: number, dados: PropriedadeInput) {
  const response = await api.patch<Propriedade>(
    `/propriedades/${id}/`,
    montarFormulario(dados),
  );
  return response.data;
}

export async function excluirPropriedade(id: number) {
  await api.delete(`/propriedades/${id}/`);
}

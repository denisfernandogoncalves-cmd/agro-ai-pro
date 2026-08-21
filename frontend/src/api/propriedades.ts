import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";
import {
  atualizarSessao,
  capturarSessao,
  estaAutenticado,
  geracaoSessaoValida,
  invalidarSessao,
  logoutExplicitoAtivo,
  obterAccessToken,
  obterGeracaoSessao,
  obterRefreshToken,
  registrarLoginExplicito,
  registrarLogoutExplicito,
} from "../auth/sessionCoordinator";
import { GeometriaGeoJSON } from "../utils/geometria";


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
  cad_pro_numeros: string[];
  criado_em: string;
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
  cad_pro_numero: string;
  arquivo_kml: File | null;
};

const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000/api";

type RequisicaoComRetry = InternalAxiosRequestConfig & {
  _retry?: boolean;
  _sessionGeneration?: string;
};

export const api = axios.create({
  baseURL: API_URL,
});

const apiSemAutenticacao = axios.create({
  baseURL: API_URL,
});

let renovacaoEmAndamento: {
  generation: string;
  promise: Promise<string>;
} | null = null;
let encerramentoEmAndamento: Promise<boolean> | null = null;

api.interceptors.request.use((config) => {
  const generation = obterGeracaoSessao();
  (config as RequisicaoComRetry)._sessionGeneration = generation;
  const token = obterAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

async function renovarAccessToken(
  generation: string,
  expectedRefresh: string,
) {
  if (
    encerramentoEmAndamento
    || logoutExplicitoAtivo()
    || !geracaoSessaoValida(generation)
  ) {
    throw new Error("Logout em andamento.");
  }
  if (obterRefreshToken() !== expectedRefresh) {
    throw new Error("Refresh token não disponível.");
  }
  const response = await apiSemAutenticacao.post<{
    access: string;
    refresh: string;
  }>(
    "/auth/token/refresh/",
    { refresh: expectedRefresh },
  );
  if (
    encerramentoEmAndamento
    || logoutExplicitoAtivo()
    || !geracaoSessaoValida(generation)
    || !atualizarSessao(
      generation,
      expectedRefresh,
      response.data.access,
      response.data.refresh,
    )
  ) {
    throw new Error("Sessão encerrada durante a renovação.");
  }
  return response.data.access;
}

api.interceptors.response.use(
  (response) => {
    const request = response.config as RequisicaoComRetry;
    if (
      request._sessionGeneration
      && !geracaoSessaoValida(request._sessionGeneration)
    ) {
      return Promise.reject(
        new axios.CanceledError("Resposta privada de sessão antiga."),
      );
    }
    return response;
  },
  async (erro: AxiosError) => {
    const requisicao = erro.config as RequisicaoComRetry | undefined;
    const endpointAutenticacao = requisicao?.url?.includes("/auth/");
    if (
      erro.response?.status !== 401
      || !requisicao
      || requisicao._retry
      || endpointAutenticacao
      || logoutExplicitoAtivo()
      || !requisicao._sessionGeneration
      || !geracaoSessaoValida(requisicao._sessionGeneration)
    ) {
      return Promise.reject(erro);
    }

    requisicao._retry = true;
    const generation = requisicao._sessionGeneration;
    const refresh = obterRefreshToken();
    if (!refresh) {
      return Promise.reject(erro);
    }

    try {
      if (
        !renovacaoEmAndamento
        || renovacaoEmAndamento.generation !== generation
      ) {
        const promise = renovarAccessToken(generation, refresh).finally(() => {
          if (renovacaoEmAndamento?.promise === promise) {
            renovacaoEmAndamento = null;
          }
        });
        renovacaoEmAndamento = { generation, promise };
      }
      const token = await renovacaoEmAndamento.promise;
      if (!geracaoSessaoValida(generation)) {
        throw new Error("Sessão encerrada antes da repetição.");
      }
      requisicao.headers.Authorization = `Bearer ${token}`;
      return api.request(requisicao);
    } catch (erroRenovacao) {
      if (
        !logoutExplicitoAtivo()
        && obterGeracaoSessao() === generation
      ) {
        invalidarSessao(generation);
      }
      return Promise.reject(erroRenovacao);
    }
  },
);

export { estaAutenticado };

export async function autenticar(username: string, password: string) {
  if (encerramentoEmAndamento) {
    await encerramentoEmAndamento;
  }
  const { generation } = capturarSessao();
  const response = await apiSemAutenticacao.post<{
    access: string;
    refresh: string;
  }>("/auth/token/", {
    username,
    password,
  });
  if (
    !registrarLoginExplicito(
      generation,
      response.data.access,
      response.data.refresh,
    )
  ) {
    throw new Error("Sessão alterada durante o login.");
  }
}

export function sair() {
  if (encerramentoEmAndamento) {
    return encerramentoEmAndamento;
  }
  const refresh = registrarLogoutExplicito();
  if (!refresh) {
    return Promise.resolve(true);
  }

  encerramentoEmAndamento = (async () => {
    try {
      await apiSemAutenticacao.post("/auth/logout/", { refresh });
      return true;
    } catch {
      return false;
    } finally {
      encerramentoEmAndamento = null;
    }
  })();
  return encerramentoEmAndamento;
}

export async function listarPropriedades(search = "") {
  const response = await api.get<Propriedade[]>("/propriedades/", {
    params: search ? { search } : undefined,
  });
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

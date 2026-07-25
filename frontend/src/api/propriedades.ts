import axios from "axios";


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
  observacoes: string;
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
  arquivo_kml: File | null;
};

const TOKEN_KEY = "agro-ai-pro.access-token";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000/api",
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export function estaAutenticado() {
  return Boolean(localStorage.getItem(TOKEN_KEY));
}

export async function autenticar(username: string, password: string) {
  const response = await api.post<{ access: string }>("/auth/token/", {
    username,
    password,
  });
  localStorage.setItem(TOKEN_KEY, response.data.access);
}

export function sair() {
  localStorage.removeItem(TOKEN_KEY);
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

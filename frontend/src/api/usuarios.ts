import { api } from "./propriedades";

export const MODULOS = [
  ["propriedades", "Propriedades"], ["talhoes", "Talhões"],
  ["cadastros-agricolas", "Cadastros agrícolas"], ["cargas", "Cargas colhidas"],
  ["producao-saldos", "Produção e saldos"], ["transferencias", "Transferência de saldo"],
  ["vendas", "Vendas"], ["clima", "Clima"], ["mercado", "Mercado"],
  ["financeiro", "Financeiro"], ["estoque", "Estoque"], ["operacoes", "Operações"],
  ["maquinas", "Máquinas"], ["faturamento-insumos", "Faturamento de insumos"],
  ["relatorios", "Relatórios"], ["importacoes", "Importações"], ["insights", "Assistente"],
] as const;
export type Modulo = typeof MODULOS[number][0];
export const ACOES = ["consultar", "cadastrar", "editar", "excluir", "imprimir"] as const;
export type Acao = typeof ACOES[number];
export type Pagina = Modulo | "usuarios" | "inicio" | "historico";
export type Usuario = { id: number; username: string; first_name: string; last_name: string; email: string; is_active: boolean; is_staff: boolean; modulos: Modulo[]; permissoes?: Partial<Record<Modulo, Acao[]>> };
export type UsuarioAtual = Pick<Usuario, "id" | "username" | "is_staff" | "modulos" | "permissoes">;
export type DadosUsuario = Omit<Usuario, "id" | "is_staff"> & { password?: string; password_confirmation?: string };
export const listarUsuarios = async () => (await api.get<Usuario[]>("/auth/users/")).data;
export const salvarUsuario = async (id: number | null, dados: DadosUsuario) => id === null
  ? (await api.post<Usuario>("/auth/users/", dados)).data
  : (await api.patch<Usuario>(`/auth/users/${id}/`, dados)).data;
export const excluirUsuario = async (id: number) => { await api.delete(`/auth/users/${id}/`); };

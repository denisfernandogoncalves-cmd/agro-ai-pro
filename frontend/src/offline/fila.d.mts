export type IdentidadeOffline = { usuario: number; servidor: string; dispositivo: string };
export function novoUUID(): string;
export type ItemOffline = IdentidadeOffline & {
  id: string; estado: string; tentativas: number; criadoEm: string;
  dados: Record<string, unknown>; registro: number | null; versao_original: string | null;
  mensagem?: string;
};
export class FilaOffline {
  constructor(storage: unknown, identidade: (online?: boolean) => Promise<IdentidadeOffline | null>, enviar: (payload: Record<string, unknown>, dono: IdentidadeOffline) => Promise<{status: number; dados?: Record<string, unknown>}>, uuid?: () => string, identidadeRecuperacao?: () => Promise<IdentidadeOffline | null>);
  exportar(): Promise<string>;
  recuperar(texto: string): Promise<number>;
  cadastrar(dados: Record<string, unknown>, original?: {registro: number; versao: string} | null): Promise<ItemOffline>;
  listar(): Promise<ItemOffline[]>;
  editar(id: string, dados: Record<string, unknown>): Promise<ItemOffline>;
  sincronizar(): Promise<ItemOffline[]>;
}

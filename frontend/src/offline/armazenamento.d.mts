export class ArmazenamentoOffline {
  salvarContexto<T>(id: string, dados: T): Promise<T>;
  lerContexto<T>(id: string): Promise<T | null>;
}

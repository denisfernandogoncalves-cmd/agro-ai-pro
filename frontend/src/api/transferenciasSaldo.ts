import { api, listarPropriedades } from "./propriedades";
import { consultarPainelSaldos, listarMovimentacoesSaldo } from "./producaoSaldos";

export type TransferenciaSaldoInput = { posicao_origem: number; posicao_destino: number; quantidade_kg: string; data_movimento: string; referencia_externa: string; observacoes: string; chave_idempotencia: string };

export async function carregarTransferenciasSaldo() {
  const [painel, movimentos, propriedades] = await Promise.all([consultarPainelSaldos(), listarMovimentacoesSaldo(), listarPropriedades()]);
  return { propriedades, posicoes: painel.posicoes, movimentos: movimentos.filter(m => m.operacao === "transferencia_saida" || m.operacao === "transferencia_entrada") };
}

export async function transferirSaldo(dados: TransferenciaSaldoInput) {
  return (await api.post("/graos/saldos/transferir/", dados)).data;
}

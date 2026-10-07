import { api, listarPropriedades } from "./propriedades";
import { consultarPainelSaldos, listarMovimentacoesSaldo } from "./producaoSaldos";
import { CADPro } from "./cargasColhidas";

export type TransferenciaSaldoInput = { posicao_origem: number; posicao_destino?: number; propriedade_destino?: number; cad_pro_destino?: string; quantidade_kg: string; data_movimento: string; referencia_externa: string; observacoes: string; chave_idempotencia: string };

export async function carregarTransferenciasSaldo() {
  const [painel, movimentos, propriedades, cadpros] = await Promise.all([consultarPainelSaldos(), listarMovimentacoesSaldo(), listarPropriedades(), api.get<CADPro[]>("/cadpros/", { params: { ativo: true } })]);
  return { propriedades, cadpros: cadpros.data, posicoes: painel.posicoes, movimentos: movimentos.filter(m => m.operacao === "transferencia_saida" || m.operacao === "transferencia_entrada") };
}

export async function transferirSaldo(dados: TransferenciaSaldoInput) {
  return (await api.post("/graos/saldos/transferir/", dados)).data;
}

export async function alterarTransferenciaSaldo(id: number, dados: TransferenciaSaldoInput & { motivo: string }) {
  return (await api.patch(`/graos/transferencias/${id}/`, dados)).data;
}
export async function excluirTransferenciaSaldo(id: number, motivo: string, chave: string) {
  return (await api.delete(`/graos/transferencias/${id}/`, { data: { motivo, chave_idempotencia: chave } })).data;
}

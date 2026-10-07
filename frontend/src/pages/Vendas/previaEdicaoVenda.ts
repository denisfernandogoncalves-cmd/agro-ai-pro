import type { AlvoEdicaoVenda } from "../../api/vendas";
import type { PosicaoSaldo } from "../../api/producaoSaldos";
export function previaEdicaoVenda(alvo: AlvoEdicaoVenda, posicoes: PosicaoSaldo[], quantidade: number, destinoId: number) {
  const venda = alvo.venda;
  const antiga = posicoes.find(p => p.id === venda.posicao);
  const destino = posicoes.find(p => p.id === destinoId);
  if (!antiga || !destino || !Number.isFinite(quantidade) || (!alvo.excluir && quantidade <= 0)) return {linhas:[], bloqueio:"Informe uma quantidade válida e uma posição disponível na consulta."};
  const entregue = Number(venda.quantidade_entregue_kg), devolvida = Number(venda.quantidade_devolvida_kg);
  const anterior = Number(alvo.movimento?.quantidade_kg ?? venda.quantidade_kg);
  const nova = alvo.excluir ? 0 : quantidade;
  let entregueNovo = entregue, devolvidaNova = devolvida, totalNovo = Number(venda.quantidade_kg), deltaFisico = 0;
  if (alvo.natureza === "venda") { totalNovo = nova; if (alvo.excluir) deltaFisico = entregue - devolvida; }
  else if (alvo.natureza === "entrega") { entregueNovo += nova - anterior; deltaFisico = anterior - nova; }
  else { devolvidaNova += nova - anterior; deltaFisico = nova - anterior; }
  let bloqueio = "";
  if (!alvo.excluir || alvo.natureza !== "venda") {
    if (devolvidaNova < 0 || devolvidaNova > entregueNovo || entregueNovo > totalNovo) bloqueio = "A quantidade conflita com o total contratado, entregue ou devolvido. Corrija os lançamentos dependentes primeiro.";
    if (alvo.natureza === "venda" && destino.id !== antiga.id && entregue > 0) bloqueio = "Corrija ou exclua as entregas antes de trocar a posição de estoque.";
  }
  const reservaAtual = Number(venda.quantidade_reservada_kg);
  const reservaNova = alvo.excluir && alvo.natureza === "venda" || ["rascunho","cancelada"].includes(venda.status) ? 0 : Math.max(0,totalNovo - entregueNovo);
  const linhas = destino.id === antiga.id || alvo.natureza !== "venda" || alvo.excluir ? [{posicao:antiga, deltaFisico, deltaReserva:reservaNova - reservaAtual}] : [
    {posicao:antiga,deltaFisico:0,deltaReserva:-reservaAtual}, {posicao:destino,deltaFisico:0,deltaReserva:reservaNova},
  ];
  return {bloqueio, linhas:linhas.map(l => ({posicao:l.posicao, anterior:Number(l.posicao.saldo_fisico_kg), posterior:Math.round((Number(l.posicao.saldo_fisico_kg)+l.deltaFisico)*1000)/1000,
    disponivel:Math.round((Number(l.posicao.saldo_disponivel_kg)+l.deltaFisico-l.deltaReserva)*1000)/1000}))};
}

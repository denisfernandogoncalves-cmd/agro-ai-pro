import { Pagina } from "../api/usuarios";
const orientacoes: Partial<Record<Pagina,string>> = {
  propriedades:"Confira o código, a área declarada e o vínculo com o CAD/PRO antes de salvar. Os talhões devem respeitar a área disponível.",
  talhoes:"Informe cultura, safra e área do talhão. Compare a soma dos talhões com a área da propriedade antes de concluir o cadastro.",
  cargas:"Confira peso bruto, tara, descontos e destinatários antes de salvar. Para transferir um depósito, abra Terceiros e escolha Transferir para outra propriedade. Cancelamentos e saldo esgotado bloqueiam essa ação.",
  "producao-saldos":"Compare saldo físico, comprometido e disponível. A composição explica os movimentos. Transferências de terceiros recebidas são estoque de origem externa e não aumentam a produção ou produtividade.",
  transferencias:"Confira origem, destino, produto, safra e saldo disponível. Registre um motivo. O estorno preserva o histórico e exige saldo disponível para reversão.",
  vendas:"Revise quantidade contratada e saldo a entregar. Na saída, confira cliente, armazém, notas e quantidade. Uma entrega cancelada permanece no histórico.",
  financeiro:"Revise vencimento e parceiro. Ao liquidar, informe a data e o valor efetivamente pago ou recebido. Uma diferença exige conferência; a liquidação encerra o título conforme a regra vigente.",
  estoque:"Confira unidade, lote, validade e local. Use o histórico para investigar diferenças antes de registrar um ajuste justificado.",
  operacoes:"Confira propriedade, talhão, safra, responsável e datas. Registre a execução para comparar custo previsto e realizado.",
  maquinas:"Confira horímetro, combustível e manutenções pendentes. Preserve a sequência dos registros para apurar consumo e custos.",
  importacoes:"Gere a prévia primeiro. Use o filtro de erros e advertências para revisar as linhas; corrija a planilha e gere uma nova prévia. A confirmação exige revisão explícita e ausência de erros.",
  relatorios:"A Central de gestão reúne documentos, checklist, conferência financeira e diagnóstico. Os relatórios usam os filtros aplicados; a exportação em Excel inclui todos os resultados, e o PDF aceita até 1.000 registros.",
};
export default function AjudaModulo({modulo}:{modulo:Pagina}) {
  const texto=orientacoes[modulo];
  return texto?<details className="card nao-imprimir"><summary>Ajuda nesta aba</summary><p>{texto}</p><p>Uma ação pode ficar indisponível por falta de permissão, dados obrigatórios, saldo ou situação do registro. Confira a mensagem exibida junto à ação.</p></details>:null;
}

type Props = { status: string; reservada: string; entregue: string; devolvida: string; excluida: boolean };
const kg = (v: string | number) => `${Number(v).toLocaleString("pt-BR", { maximumFractionDigits: 3 })} kg`;
export default function FluxoVenda({ status, reservada, entregue, devolvida, excluida }: Props) {
  const cancelada = excluida || status === "cancelada";
  const etapas = [
    ["Contrato", status === "rascunho" ? "Rascunho" : cancelada ? "Cancelado / histórico" : "Registrado"],
    ["Reserva atual", kg(reservada)],
    ["Entregas registradas", kg(entregue)],
    ["Baixa física líquida", kg(Number(entregue) - Number(devolvida))],
  ];
  return <div className="fluxo-venda nao-imprimir"><ol aria-label="Fluxo físico do contrato">{etapas.map(([titulo, valor], i) => <li key={titulo}><span className="fluxo-etapa" aria-hidden="true">{i + 1}</span><div><strong>{titulo}</strong><small>{valor}</small></div></li>)}</ol><p>Entrega e baixa física seguem os registros existentes; devoluções reduzem a saída líquida. Situação: {status}{excluida ? " · excluído do cadastro ativo" : ""}.</p></div>;
}

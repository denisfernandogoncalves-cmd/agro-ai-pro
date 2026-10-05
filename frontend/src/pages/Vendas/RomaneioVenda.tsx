import ComprovanteLancamento, { DadosComprovante } from "../../components/ComprovanteLancamento";
import { MovimentoVenda, VendaGraos } from "../../api/vendas";
import { formatarNumero } from "../../utils/numeros";

export function dadosRomaneioVenda(venda: VendaGraos, saida: MovimentoVenda): DadosComprovante {
  return {
    titulo: `Romaneio de saída #${saida.id} · Venda #${venda.id}`,
    campos: [
      ["Situação", venda.excluida_em || saida.cancelado_em ? "Cancelada/excluída — histórico" : "Saída registrada"],
      ["Data da saída", saida.data_entrega?.slice(0, 10).split("-").reverse().join("/") || "—"],
      ["Propriedade / CAD/PRO", `${venda.propriedade_nome || "—"} / ${venda.cad_pro_codigo}`],
      ["Destino / comprador", saida.destino || venda.cliente_nome || "—"],
      ["Contrato", venda.numero_contrato || "Sem contrato"],
      ["Cultura / safra", `${venda.cultura} / ${venda.safra}`],
      ["Classificação", venda.classificacao_codigo],
      ["Armazenagem", venda.armazem_nome],
      ["Placa", saida.placa || "Sem placa"],
      ["Motorista", saida.motorista || "—"],
      ["Nota do produtor", saida.nota_produtor || "—"],
      ["Nota da empresa", saida.nota_empresa || "—"],
      ["Peso bruto", saida.peso_bruto_kg==null?"Não informado":`${formatarNumero(saida.peso_bruto_kg)} kg`],
      ["Tara", saida.tara_kg==null?"Não informada":`${formatarNumero(saida.tara_kg)} kg`],
      ["Qualidade (apenas informativa)", `Umidade ${saida.umidade_percentual??"—"}% · Avariados ${saida.avariados_percentual??"—"}% · Quebrados ${saida.quebrados_percentual??"—"}% · PH ${saida.ph??"—"}`],
      ["Peso líquido", `${formatarNumero(saida.quantidade_kg)} kg`],
      ["Sacas de 60 kg", formatarNumero(Number(saida.quantidade_kg) / 60)],
      ["Movimento", String(saida.movimentacao_id)],
      ["Referência", saida.referencia_externa || "—"],
      ["Observações", saida.observacoes || venda.observacoes || "—"],
    ],
  };
}

export default function RomaneiosVenda({ venda }: { venda: VendaGraos }) {
  return <section className="nao-imprimir" aria-label="Romaneios de saída">
    <h4>Romaneios de saída</h4>
    {venda.entregas.length ? venda.entregas.map(saida => <div className="acoes" key={saida.id}>
      <span>Saída #{saida.id} · {formatarNumero(saida.quantidade_kg)} kg{saida.cancelado_em ? " · Cancelada" : ""}</span>
      <ComprovanteLancamento dados={dadosRomaneioVenda(venda, saida)} rotulo="Imprimir romaneio" tipoDocumento="romaneio" />
    </div>) : <p>O romaneio estará disponível após registrar uma saída de grãos.</p>}
  </section>;
}

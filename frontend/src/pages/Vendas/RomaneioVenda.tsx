import ComprovanteLancamento, { DadosComprovante } from "../../components/ComprovanteLancamento";
import { MovimentoVenda, VendaGraos } from "../../api/vendas";
import { formatarNumero } from "../../utils/numeros";

function formatarPreco(valor: string | number) {
  return Number(valor).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function valorNegociadoDaSaida(venda: VendaGraos, saida: MovimentoVenda): [string, string][] {
  const preco = Number(venda.contrato_preco_venda);
  const pesoLiquido = Number(saida.quantidade_kg);
  if (!Number.isFinite(preco) || preco <= 0 || !Number.isFinite(pesoLiquido) || pesoLiquido < 0) return [];
  const quantidadeNegociada = venda.contrato_unidade_preco === "sc" ? pesoLiquido / 60 : pesoLiquido;
  return [["Valor negociado", `R$ ${formatarPreco(quantidadeNegociada * preco)}`]];
}

export function dadosRomaneioVenda(venda: VendaGraos, saida: MovimentoVenda): DadosComprovante {
  return {
    titulo: `Romaneio de saída #${saida.id} · Venda #${venda.id}`,
    modelo: "romaneio",
    campos: [
      ["Situação", venda.excluida_em || saida.cancelado_em ? "Cancelada/excluída — histórico" : "Saída registrada"],
      ["Data da saída", saida.data_entrega?.slice(0, 10).split("-").reverse().join("/") || "—"],
      ["Propriedade / CAD/PRO", `${venda.propriedade_nome || "—"} / ${venda.cad_pro_codigo}`],
      ["Destino / comprador", saida.destino || venda.cliente_nome || "—"],
      ["Contrato", venda.numero_contrato || "Sem contrato"],
      ["Cultura / safra", `${venda.cultura} / ${venda.safra}`],
      ["Armazenagem", venda.armazem_nome],
      ["Motorista", saida.motorista || "—"],
      ["Placa", saida.placa || "Sem placa"],
      ["Nota do produtor", saida.nota_produtor || "—"],
      ["Peso bruto", saida.peso_bruto_kg==null?"Não informado":`${formatarNumero(saida.peso_bruto_kg)} kg`],
      ["Tara", saida.tara_kg==null?"Não informada":`${formatarNumero(saida.tara_kg)} kg`],
      ["Peso líquido", `${formatarNumero(saida.quantidade_kg)} kg`],
      ["Qualidade", `Umidade ${saida.umidade_percentual??"—"}% · Avariados ${saida.avariados_percentual??"—"}% · Quebrados ${saida.quebrados_percentual??"—"}%${venda.cultura.toLowerCase()==="trigo"?` · PH ${saida.ph??"—"}`:""}`],
      ["Sacas de 60 kg", formatarNumero(Number(saida.quantidade_kg) / 60)],
      ["Movimento", String(saida.movimentacao_id)],
      ["Referência", saida.referencia_externa || "—"],
      ["Observações", saida.observacoes || venda.observacoes || "—"],
    ],
    camposViaArquivo: venda.contrato_preco_venda ? valorNegociadoDaSaida(venda, saida) : [],
  };
}

export default function RomaneiosVenda({ venda }: { venda: VendaGraos }) {
  return <section className="nao-imprimir" aria-label="Romaneios de saída">
    <h4>Romaneios de saída</h4>
    {venda.entregas.length ? venda.entregas.map(saida => <div className="acoes" key={saida.id}>
      <span>Saída #{saida.id} · {formatarNumero(saida.quantidade_kg)} kg{saida.cancelado_em ? " · Cancelada" : ""}</span>
      <ComprovanteLancamento duasVias dados={dadosRomaneioVenda(venda, saida)} rotulo="Imprimir romaneio" tipoDocumento="romaneio" downloadRomaneio={{vendaId:venda.id,saidaId:saida.id}} />
    </div>) : <p>O romaneio estará disponível após registrar uma saída de grãos.</p>}
  </section>;
}

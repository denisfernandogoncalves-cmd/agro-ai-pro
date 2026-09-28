import { LancamentoFinanceiro, ResumoFinanceiro } from "../../api/financeiro";

const moeda = (valor: string | null) => valor === null ? "—" : Number(valor).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const data = (valor: string | null) => valor ? valor.split("-").reverse().join("/") : "—";

type Props = {
  lancamentos: LancamentoFinanceiro[];
  resumo: ResumoFinanceiro | null;
  filtros: string;
  carregando: boolean;
};

export default function FinanceiroImpressao({ lancamentos, resumo, filtros, carregando }: Props) {
  return <section className="financeiro-impressao somente-impressao">
    {carregando ? <p>Aguarde o carregamento dos lançamentos antes de imprimir.</p> : <>
      <p className="financeiro-impressao-filtros">{filtros}</p>
      {resumo && <dl className="financeiro-impressao-resumo">
        {([
          ["A pagar", resumo.a_pagar], ["Pagos", resumo.saidas_realizadas],
          ["A receber", resumo.a_receber], ["Saldo previsto", resumo.saldo_previsto],
          ["Saldo realizado", resumo.saldo_realizado], ["Em atraso", resumo.valor_atrasado],
        ] as const).map(([nome, valor]) => <div key={nome}><dt>{nome}</dt><dd>R$ {moeda(valor)}</dd></div>)}
      </dl>}
      <table className="financeiro-impressao-tabela">
        <caption>{lancamentos.length} lançamento(s) na consulta · Valores em R$</caption>
        <colgroup><col style={{ width: "12%" }} /><col style={{ width: "33%" }} /><col style={{ width: "6%" }} /><col style={{ width: "12%" }} /><col style={{ width: "12%" }} /><col style={{ width: "12%" }} /><col style={{ width: "13%" }} /></colgroup>
        <thead><tr><th>Situação</th><th>Descrição / favorecido</th><th>Boleto</th><th>Vencimento</th><th>Liquidação</th><th className="numero">Valor</th><th className="numero">Liquidado</th></tr></thead>
        <tbody>{lancamentos.length ? lancamentos.map(item => <tr key={item.id}>
          <td>{item.status === "cancelado" ? "Cancelado" : item.status === "liquidado" ? (item.tipo === "pagar" ? "Pago" : "Recebido") : (item.tipo === "pagar" ? "A pagar" : "A receber")}{item.atrasado && <small>Em atraso</small>}</td>
          <td><strong>{item.descricao}</strong><span>{item.recebedor_nome || item.parceiro_nome || "Não informado"}</span>{item.codigo_barras && <small className="codigo-impressao">Código: {item.codigo_barras}</small>}</td>
          <td>{item.parcela_numero ? `${item.parcela_numero}${item.total_boletos ? `/${item.total_boletos}` : ""}` : "—"}</td>
          <td>{data(item.data_vencimento)}</td><td>{data(item.data_liquidacao)}</td>
          <td className="numero">{moeda(item.valor)}</td><td className="numero">{moeda(item.valor_liquidado)}</td>
        </tr>) : <tr><td colSpan={7}>Nenhum lançamento encontrado para esta consulta.</td></tr>}</tbody>
      </table>
    </>}
  </section>;
}

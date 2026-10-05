import { FormEvent, useEffect, useRef, useState } from "react";
import { DisponibilidadeEstoque, listarDisponibilidadeEstoque, ProdutoEstoque, ResumoDisponibilidade } from "../../api/estoque";
import { ParceiroFinanceiro } from "../../api/financeiro";

const numero = (valor: string, casas = 3) => Number(valor).toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });
const data = (valor: string) => valor.split("-").reverse().join("/");

export function TabelaDisponibilidade({ itens }: { itens: DisponibilidadeEstoque[] }) {
  if (!itens.length) return <p>Nenhum estoque encontrado para os filtros selecionados.</p>;
  return <div className="tabela-saldos" style={{ overflowX: "auto" }}><table>
    <thead><tr><th>Produto</th><th>Fornecedor</th><th>Data da compra / entrada</th><th>Comprado</th><th>Saídas</th><th>Disponível</th><th>Preço médio por unidade</th><th>Valor de aquisição</th></tr></thead>
    <tbody>{itens.map((item) => <tr key={`${item.produto_id}-${item.fornecedor_id}-${item.data_compra}`}>
      <td>{item.produto}<details><summary>Lotes</summary>{item.lotes.map((lote) => <p key={lote.id}>{lote.codigo}: {lote.datas_entrada.map(data).join(", ")}</p>)}</details></td>
      <td>{item.fornecedor}</td><td>{item.data_compra ? data(item.data_compra) : (item.lotes.every(l => !l.datas_entrada.length) ? "Sem entrada — faturamento" : "Datas múltiplas — saldo conjunto do lote")}</td>
      <td>{numero(item.quantidade_comprada)} {item.unidade}</td><td>{numero(item.quantidade_saida)} {item.unidade}</td>
      <td><strong>{numero(item.disponivel)} {item.unidade}</strong></td>
      <td>{item.preco_medio === null ? "Custo incompleto" : `R$ ${numero(item.preco_medio, 4)} / ${item.unidade}`}</td>
      <td>{item.valor_aquisicao === null ? "Custo incompleto" : `R$ ${numero(item.valor_aquisicao, 2)}`}</td>
    </tr>)}</tbody>
  </table></div>;
}

type Props = { produtos: ProdutoEstoque[]; fornecedores: ParceiroFinanceiro[]; revisao: number };

export function ResumoPorFornecedor({ itens }: { itens: ResumoDisponibilidade[] }) {
  const grupos = new Map<number | null, ResumoDisponibilidade[]>();
  itens.forEach(item => grupos.set(item.fornecedor_id, [...(grupos.get(item.fornecedor_id) || []), item]));
  return <section className="disponibilidade-fornecedores" aria-label="Produtos agrupados por fornecedor">
    {[...grupos.entries()].map(([id, produtos]) => <section className="disponibilidade-fornecedor" key={id ?? "sem-fornecedor"}>
      <div className="disponibilidade-fornecedor-titulo"><h3>{produtos[0].fornecedor || "Sem fornecedor"}</h3><span>{produtos.length} produto(s)</span></div>
      <div className="disponibilidade-tabela-scroll"><table>
        <thead><tr><th>Produto</th><th className="numero">Saldo disponível</th><th className="numero">Preço médio / unidade</th></tr></thead>
        <tbody>{produtos.map(item => <tr key={item.produto_id}><td>{item.produto}</td><td className="numero"><strong>{numero(item.disponivel)} {item.unidade}</strong></td><td className="numero">{item.preco_medio === null ? "Custo incompleto" : `R$ ${numero(item.preco_medio, 4)} / ${item.unidade}`}</td></tr>)}</tbody>
      </table></div>
    </section>)}
  </section>;
}

export default function ConsultaDisponibilidade({ produtos, fornecedores, revisao }: Props) {
  const [filtros, setFiltros] = useState({ produto: "", fornecedor: "", data_inicio: "", data_fim: "", somente_disponivel: "false" });
  const [aplicados, setAplicados] = useState(filtros);
  const [resumo, setResumo] = useState<ResumoDisponibilidade[]>([]);
  const [itens, setItens] = useState<DisponibilidadeEstoque[]>([]);
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(false);
  const [atualizacao, setAtualizacao] = useState(0);
  const sequencia = useRef(0);
  useEffect(() => {
    const requisicao = ++sequencia.current;
    setCarregando(true); setErro(""); setItens([]); setResumo([]);
    const params = Object.fromEntries(Object.entries(aplicados).filter(([, valor]) => valor !== ""));
    listarDisponibilidadeEstoque(params).then((dados) => {
      if (requisicao === sequencia.current) { setItens(dados.itens); setResumo(dados.resumo); }
    }).catch(() => {
      if (requisicao === sequencia.current) setErro("Não foi possível consultar o estoque. Confira as datas e tente novamente.");
    }).finally(() => { if (requisicao === sequencia.current) setCarregando(false); });
    return () => { sequencia.current++; };
  }, [aplicados, revisao, atualizacao]);
  function consultar(evento: FormEvent) { evento.preventDefault(); setAplicados({ ...filtros }); setAtualizacao((valor) => valor + 1); }
  return <details open className="card estoque-disponibilidade"><summary>Disponibilidade por fornecedor e data da compra</summary>
    <h2>Saldo e preço médio de aquisição</h2>
    <p>Consulte os produtos de cada fornecedor, com saldo atual e preço médio das compras selecionadas.</p>
    <details className="disponibilidade-ajuda"><summary>Como os valores são calculados</summary>
      <p>Preço médio = valor total de aquisição ÷ quantidade comprada, em R$ por unidade do produto. Usa o preço registrado na compra; não indica quitação financeira.</p>
      <p>O saldo considera todas as saídas, inclusive posteriores ao período filtrado. Lotes com entradas em datas diferentes aparecem com saldo conjunto, sem atribuição presumida das saídas a cada compra.</p>
    </details>
    <form className="disponibilidade-filtros" onSubmit={consultar}>
      <label>Produto<select value={filtros.produto} onChange={(e) => setFiltros({ ...filtros, produto: e.target.value })}><option value="">Todos os produtos</option>{produtos.map((p) => <option key={p.id} value={p.id}>{p.nome} ({p.unidade})</option>)}</select></label>
      <label>Fornecedor<select value={filtros.fornecedor} onChange={(e) => setFiltros({ ...filtros, fornecedor: e.target.value })}><option value="">Todos os fornecedores</option>{fornecedores.map((f) => <option key={f.id} value={f.id}>{f.nome}</option>)}</select></label>
      <label>Compra desde<input type="date" value={filtros.data_inicio} max={filtros.data_fim || undefined} onChange={(e) => setFiltros({ ...filtros, data_inicio: e.target.value })} /></label>
      <label>Compra até<input type="date" value={filtros.data_fim} min={filtros.data_inicio || undefined} onChange={(e) => setFiltros({ ...filtros, data_fim: e.target.value })} /></label>
      <label className="disponibilidade-checkbox"><input type="checkbox" checked={filtros.somente_disponivel === "true"} onChange={(e) => setFiltros({ ...filtros, somente_disponivel: String(e.target.checked) })} />Somente com saldo positivo</label>
      <button type="submit" disabled={carregando}>Consultar</button>
    </form>
    {!carregando && !erro && resumo.length > 0 && <ResumoPorFornecedor itens={resumo} />}
    {erro && <p className="erro" role="alert">{erro}</p>}
    {carregando ? <p role="status">Consultando estoque…</p> : !erro && (itens.length ? <details className="disponibilidade-detalhes"><summary>Detalhar compras e lotes por data ({itens.length} registros)</summary><TabelaDisponibilidade itens={itens} /></details> : <TabelaDisponibilidade itens={itens} />)}
  </details>;
}

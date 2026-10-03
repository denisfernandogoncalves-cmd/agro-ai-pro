import AnexosLancamento from "../../components/AnexosLancamento";
import { FormEvent, useEffect, useRef, useState } from "react";
import axios from "axios";
import PainelFormulario from "../../components/PainelFormulario";
import { CompraEstoque, CompraEstoqueInput, ProdutoEstoque, listarComprasEstoque, registrarCompraEstoque } from "../../api/estoque";
import { ParceiroFinanceiro } from "../../api/financeiro";

const colunas = ["DATA DA COMPRA", "PRODUTO", "CULTURA", "SAFRA", "QTD", "PCT", "L / KG", "FORNECEDOR", "CUSTO UNITÁRIO", "DATA DE VENCIMENTO", "QT EM LITROS / KG", "VALOR / L OU KG", "VALOR TOTAL"];
const numero = (valor: string | number, casas = 3) => Number(valor).toLocaleString("pt-BR", { maximumFractionDigits: casas });
const moeda = (valor: string | number) => Number(valor).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const data = (valor: string | null) => valor ? valor.split("-").reverse().join("/") : "—";
function inicial(): CompraEstoqueInput {
  const agora = new Date();
  const hoje = `${agora.getFullYear()}-${String(agora.getMonth() + 1).padStart(2, "0")}-${String(agora.getDate()).padStart(2, "0")}`;
  return { id: "", data_compra: hoje, produto: "", cultura: "", safra: "", quantidade_embalagens: "", embalagem: "", conteudo_embalagem: "", fornecedor: "", custo_embalagem: "", data_vencimento: "" };
}

export default function ComprasEstoque({ produtos, fornecedores, atualizarEstoque }: {
  produtos: ProdutoEstoque[]; fornecedores: ParceiroFinanceiro[]; atualizarEstoque: () => Promise<void>;
}) {
  const [form, setForm] = useState(inicial);
  const [compras, setCompras] = useState<CompraEstoque[]>([]);
  const [busca, setBusca] = useState("");
  const [erro, setErro] = useState("");
  const [sucesso, setSucesso] = useState("");
  const [salvando, setSalvando] = useState(false);
  const [carregando, setCarregando] = useState(false);
  const trava = useRef(false);
  const chave = useRef<string | null>(null);
  const produto = produtos.find(p => String(p.id) === form.produto);
  const qtd = Number(form.quantidade_embalagens);
  const conteudo = Number(form.conteudo_embalagem);
  const custo = Number(form.custo_embalagem);
  const temQuantidade = qtd > 0 && conteudo > 0;
  const temCusto = form.custo_embalagem !== "" && custo >= 0;
  function alterar(campo: keyof CompraEstoqueInput, valor: string) {
    setForm(atual => ({ ...atual, [campo]: valor }));
  }
  function falha(exc: unknown) {
    if (axios.isAxiosError(exc) && exc.response?.data) {
      const dados = exc.response.data;
      return typeof dados === "string" ? "Não foi possível registrar a compra." : Object.values(dados).flat().join(" ");
    }
    return "Não foi possível concluir a operação. Tente novamente.";
  }
  async function carregar(termo = "") {
    setCarregando(true);
    try { setCompras(await listarComprasEstoque(termo)); }
    catch (exc) { setErro(falha(exc)); }
    finally { setCarregando(false); }
  }
  useEffect(() => { void carregar(); }, []);
  async function salvar(evento: FormEvent) {
    evento.preventDefault();
    if (trava.current) return;
    trava.current = true;
    setSalvando(true); setErro(""); setSucesso("");
    try {
      chave.current ??= crypto.randomUUID();
      await registrarCompraEstoque({ ...form, id: chave.current });
      chave.current = null;
      setForm(inicial());
      setSucesso("Compra registrada e quantidade adicionada ao estoque.");
      await Promise.all([carregar(busca), atualizarEstoque()]);
    } catch (exc) { setErro(falha(exc)); }
    finally { trava.current = false; setSalvando(false); }
  }
  return <section className="compras-estoque">
    {erro && <p className="erro card" role="alert">{erro}</p>}
    {sucesso && <p className="sucesso card" role="status">{sucesso}</p>}
    <PainelFormulario titulo="Nova compra de estoque">
    <form className="card" onSubmit={salvar}>
      <h2>Nova compra</h2>
      <fieldset disabled={salvando} className="compra-campos">
        <label>Data da compra<input required type="date" value={form.data_compra} onChange={e => alterar("data_compra", e.target.value)} /></label>
        <label>Produto<select required value={form.produto} onChange={e => alterar("produto", e.target.value)}><option value="">Selecione</option>{produtos.filter(p => p.ativo && ["l", "kg"].includes(p.unidade)).map(p => <option key={p.id} value={p.id}>{p.nome} ({p.unidade.toUpperCase()})</option>)}</select></label>
        <label>Cultura<input maxLength={100} list="culturas-compra" placeholder="Ex.: Soja" value={form.cultura} onChange={e => alterar("cultura", e.target.value)} /></label>
        <label>Safra<input maxLength={20} placeholder="Ex.: 2026" value={form.safra} onChange={e => alterar("safra", e.target.value)} /></label>
        <datalist id="culturas-compra">{["Soja", "Milho", "Trigo", "Feijão", "Café"].map(c => <option key={c} value={c} />)}</datalist>
        <label>QTD<input required type="number" min="0.001" max="99999999999.999" step="0.001" value={form.quantidade_embalagens} onChange={e => alterar("quantidade_embalagens", e.target.value)} /><small>Quantidade de embalagens</small></label>
        <label>PCT<input required maxLength={20} list="embalagens-compra" placeholder="BAG, GL, PCT, BD…" value={form.embalagem} onChange={e => alterar("embalagem", e.target.value)} /><small>Tipo de embalagem</small></label>
        <datalist id="embalagens-compra">{["BAG", "GL", "PCT", "BD", "SC", "CX"].map(e => <option key={e} value={e} />)}</datalist>
        <label>L / KG<input required type="number" min="0.001" max="99999999999.999" step="0.001" value={form.conteudo_embalagem} onChange={e => alterar("conteudo_embalagem", e.target.value)} /><small>Conteúdo de cada embalagem{produto ? ` em ${produto.unidade.toUpperCase()}` : ""}</small></label>
        <label>Fornecedor<select required value={form.fornecedor} onChange={e => alterar("fornecedor", e.target.value)}><option value="">Selecione</option>{fornecedores.filter(f => f.ativo).map(f => <option key={f.id} value={f.id}>{f.nome}</option>)}</select></label>
        <label>Custo unitário<input required type="number" min="0" max="9999999999.9999" step="0.0001" value={form.custo_embalagem} onChange={e => alterar("custo_embalagem", e.target.value)} /><small>Preço por embalagem em R$</small></label>
        <label>Data de vencimento<input type="date" value={form.data_vencimento} onChange={e => alterar("data_vencimento", e.target.value)} /><small>Vencimento do pagamento</small></label>
        <label>QT em litros / kg<output>{temQuantidade ? `${numero(qtd * conteudo)} ${produto?.unidade.toUpperCase() || ""}` : "—"}</output></label>
        <label>Valor / L ou kg<output>{temQuantidade && temCusto ? moeda(custo / conteudo) : "—"}</output></label>
        <label>Valor total<output>{temQuantidade && temCusto ? moeda(qtd * custo) : "—"}</output></label>
      </fieldset>
      <div className="compra-rodape"><p>Selecione produtos em litros ou kg. Produtos e fornecedores são cadastrados em Cadastros agrícolas.</p><button type="submit" disabled={salvando}>{salvando ? "Salvando…" : "Registrar compra"}</button></div>
    </form>
    </PainelFormulario>
    <section className="card compras-lista-impressao">
      <div className="compra-lista-cabecalho"><h2>Compras de estoque</h2><form className="busca" onSubmit={e => { e.preventDefault(); setErro(""); void carregar(busca); }}><input aria-label="Buscar compras" placeholder="Produto, cultura ou fornecedor" value={busca} onChange={e => setBusca(e.target.value)} /><button disabled={carregando}>Buscar</button></form></div>
      <div className="compra-tabela-scroll" tabIndex={0} role="region" aria-label="Tabela de compras de estoque">
        <table className="compra-tabela"><thead><tr>{colunas.map(c => <th scope="col" key={c}>{c}</th>)}</tr></thead>
          <tbody>{compras.map(c => <tr key={c.id}><td>{data(c.data_compra)}</td><td>{c.produto_nome}</td><td>{c.cultura || "—"}</td><td>{c.safra || "—"}</td><td>{numero(c.quantidade_embalagens)}</td><td>{c.embalagem}</td><td>{numero(c.conteudo_embalagem)} {c.unidade.toUpperCase()}</td><td>{c.fornecedor_nome}</td><td>{moeda(c.custo_embalagem)}</td><td>{data(c.data_vencimento)}</td><td>{numero(c.quantidade_total)} {c.unidade.toUpperCase()}</td><td title={`${numero(c.valor_por_unidade, 4)} por ${c.unidade}`}>{moeda(c.valor_por_unidade)}</td><td>{moeda(c.valor_total)}<AnexosLancamento entidade="compra" registro={c.id}/></td></tr>)}</tbody>
        </table>
      </div>
      {carregando ? <p role="status">Carregando compras…</p> : !compras.length && <p className="vazio">Nenhuma compra encontrada. Movimentações anteriores continuam disponíveis abaixo.</p>}
    </section>
  </section>;
}

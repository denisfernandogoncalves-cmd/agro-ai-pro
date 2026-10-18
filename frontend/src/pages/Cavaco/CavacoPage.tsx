import { FormEvent, useEffect, useState } from "react";
import axios from "axios";
import { BotaoAcao, useAcoes } from "../../components/AcoesContext";
import { useConfirmacaoCompacta } from "../../components/ConfirmacaoCompacta";
import { abrirRomaneioCavaco, CargaCavaco, CargaCavacoInput, excluirCavaco, FiltrosCavaco, listarCavaco, salvarCavaco } from "../../api/cavaco";

const numero = (v: string | number, casas = 3) => Number(v).toLocaleString("pt-BR", { maximumFractionDigits: casas });
const moeda = (v: string | number) => Number(v).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const novo = (): CargaCavacoInput => ({ data: new Date().toLocaleDateString("sv-SE", { timeZone: "America/Sao_Paulo" }), motorista: "", fornecedor: "", placa: "", valor_tonelada: "", peso_bruto: "", tara: "", pago: false, observacoes: "" });
function mensagem(erro: unknown) {
  if (axios.isAxiosError(erro) && erro.response?.data && typeof erro.response.data === "object") return Object.values(erro.response.data).flat().join(" ");
  return erro instanceof Error ? erro.message : "Não foi possível concluir a operação.";
}

export default function CavacoPage() {
  const pode = useAcoes();
  const confirmar = useConfirmacaoCompacta();
  const [cargas, setCargas] = useState<CargaCavaco[]>([]);
  const [form, setForm] = useState(novo);
  const [id, setId] = useState<number>();
  const [filtros, setFiltros] = useState<FiltrosCavaco>({ search: "", pago: "", data_inicio: "", data_fim: "" });
  const [erro, setErro] = useState("");
  const [aviso, setAviso] = useState("");
  const [carregando, setCarregando] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [excluindo, setExcluindo] = useState<number>();
  async function carregar() {
    setCarregando(true); setErro("");
    try { setCargas(await listarCavaco(filtros)); }
    catch (e) { setCargas([]); setErro(mensagem(e)); }
    finally { setCarregando(false); }
  }
  useEffect(() => { void carregar(); }, []);
  const campo = <K extends keyof CargaCavacoInput>(k: K, v: CargaCavacoInput[K]) => setForm(atual => ({ ...atual, [k]: v }));
  const filtro = (k: keyof FiltrosCavaco, v: string) => setFiltros(atual => ({ ...atual, [k]: v }));
  const liquido = Number(form.peso_bruto) - Number(form.tara);
  const valido = form.peso_bruto !== "" && form.tara !== "" && liquido > 0;
  async function salvar(e: FormEvent) {
    e.preventDefault(); setSalvando(true); setErro(""); setAviso("");
    try {
      const carga = await salvarCavaco(form, id);
      setForm(novo()); setId(undefined);
      await carregar(); setAviso(`Carga nº ${carga.id} salva. Use “Romaneio — 2 vias” para imprimir.`);
    } catch (e) { setErro(mensagem(e)); }
    finally { setSalvando(false); }
  }
  async function imprimir(carga: CargaCavaco) {
    setErro("");
    try { await abrirRomaneioCavaco(carga.id); } catch (e) { setErro(mensagem(e)); }
  }
  async function excluir(carga: CargaCavaco) {
    if (!(await confirmar({ titulo: `Excluir carga nº ${carga.id}?`, mensagem: `${carga.fornecedor} · ${carga.data.split("-").reverse().join("/")} · ${moeda(carga.total)}. A carga sairá da lista e dos totais. O histórico será preservado.`, confirmar: "Excluir carga", perigo: true }))) return;
    setExcluindo(carga.id); setErro(""); setAviso("");
    try {
      await excluirCavaco(carga.id);
      if (id === carga.id) { setId(undefined); setForm(novo()); }
      await carregar(); setAviso(`Carga nº ${carga.id} excluída. Histórico preservado.`);
    } catch (e) { setErro(mensagem(e)); }
    finally { setExcluindo(undefined); }
  }
  const total = cargas.reduce((s, c) => s + Number(c.total), 0);
  const pendente = cargas.filter(c => c.pagamento_financeiro ? c.pagamento_financeiro === "pendente" : !c.pago).reduce((s, c) => s + Number(c.total), 0);
  const liquidado = cargas.filter(c => c.pagamento_financeiro ? c.pagamento_financeiro === "liquidado" : c.pago).reduce((s, c) => s + Number(c.total), 0);
  return <>
    {erro && <p className="erro" role="alert">{erro}</p>}
    {aviso && <p role="status">{aviso}</p>}
    {(pode("cadastrar") || (id && pode("editar"))) && <section className="card">
      <h2>{id ? `Editar carga nº ${id}` : "Nova carga de cavaco"}</h2>
      <p>Pesos em quilogramas. Peso líquido = bruto − tara. Total = peso líquido ÷ 1.000 × valor por tonelada.</p>
      <form onSubmit={salvar}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "1rem", marginBottom: "1rem" }}>
          <label>Data<input type="date" required value={form.data} onChange={e => campo("data", e.target.value)} /></label>
          <label>Motorista<input required maxLength={120} value={form.motorista} onChange={e => campo("motorista", e.target.value)} /></label>
          <label>Fornecedor<input required maxLength={160} value={form.fornecedor} onChange={e => campo("fornecedor", e.target.value)} /></label>
          <label>Placa<input maxLength={10} value={form.placa} onChange={e => campo("placa", e.target.value.toUpperCase())} /></label>
          <label>Valor por tonelada (R$)<input type="number" required min="0" step="0.01" value={form.valor_tonelada} onChange={e => campo("valor_tonelada", e.target.value)} /></label>
          <label>Peso bruto (kg)<input type="number" required min="0.001" step="0.001" value={form.peso_bruto} onChange={e => campo("peso_bruto", e.target.value)} /></label>
          <label>Tara (kg)<input type="number" required min="0" step="0.001" value={form.tara} onChange={e => campo("tara", e.target.value)} /></label>
          <label>Pagamento indicado na origem<select value={String(form.pago)} onChange={e => campo("pago", e.target.value === "true")}><option value="false">Pendente</option><option value="true">Pago</option></select></label>
          <label>Vencimento no Financeiro<input type="date" value={form.data_vencimento || form.data} onChange={e => campo("data_vencimento", e.target.value)} /></label>
        </div>
        <label>Observações<textarea maxLength={240} value={form.observacoes} onChange={e => campo("observacoes", e.target.value)} /></label>
        <p>Cada carga gera uma conta a pagar pendente. O pagamento indicado na origem é histórico; confirme a baixa no Financeiro. O vencimento pode ser ajustado neste formulário.</p>
        <p>Peso líquido: <strong>{valido ? `${numero(liquido)} kg` : "—"}</strong> · Total estimado: <strong>{valido && form.valor_tonelada !== "" ? moeda(liquido / 1000 * Number(form.valor_tonelada)) : "—"}</strong></p>
        {!valido && form.peso_bruto !== "" && form.tara !== "" && <p role="alert">A tara deve ser menor que o peso bruto.</p>}
        <BotaoAcao acao={id ? "editar" : "cadastrar"} disabled={salvando || excluindo !== undefined || !valido}>{salvando ? "Salvando…" : "Salvar carga"}</BotaoAcao>{id && <button type="button" className="secundario" disabled={salvando || excluindo !== undefined} onClick={() => { setId(undefined); setForm(novo()); }}>Cancelar edição</button>}
      </form>
    </section>}
    <section className="card">
      <h2>Controle de cavaco</h2>
      <form className="filtros-relatorio" onSubmit={e => { e.preventDefault(); void carregar(); }}>
        <label>Motorista, fornecedor ou placa<input type="search" value={filtros.search} onChange={e => filtro("search", e.target.value)} /></label>
        <label>De<input type="date" value={filtros.data_inicio} onChange={e => filtro("data_inicio", e.target.value)} /></label>
        <label>Até<input type="date" min={filtros.data_inicio} value={filtros.data_fim} onChange={e => filtro("data_fim", e.target.value)} /></label>
        <label>Pagamento na origem<select value={filtros.pago} onChange={e => filtro("pago", e.target.value)}><option value="">Todos</option><option value="false">Pendente</option><option value="true">Pago</option></select></label>
        <button disabled={carregando}>Filtrar</button>
      </form>
      {carregando ? <p role="status">Carregando cargas…</p> : <>
        <p><strong>{cargas.length} cargas</strong> · {numero(cargas.reduce((s, c) => s + Number(c.peso_liquido), 0) / 1000)} t · Total: <strong>{moeda(total)}</strong> · Baixado no Financeiro: {moeda(liquidado)} · Pendente: <strong>{moeda(pendente)}</strong></p>
        {!cargas.length ? <p>Nenhuma carga encontrada.</p> : <div style={{ overflowX: "auto" }}><table><thead><tr>{["Nº", "Data", "Motorista / placa", "Fornecedor", "Bruto (kg)", "Tara (kg)", "Líquido (kg)", "R$/t", "Total", "Pagamento (origem)", "Financeiro / vencimento", "Ações"].map(t => <th key={t}>{t}</th>)}</tr></thead><tbody>{cargas.map(c => <tr key={c.id}>
          <td>{c.id}</td><td>{c.data.split("-").reverse().join("/")}</td><td>{c.motorista}{c.placa && ` · ${c.placa}`}</td><td>{c.fornecedor}</td><td>{numero(c.peso_bruto)}</td><td>{numero(c.tara)}</td><td>{numero(c.peso_liquido)}</td><td>{moeda(c.valor_tonelada)}</td><td>{moeda(c.total)}</td><td>{c.pago ? "Pago" : "Pendente"}</td><td>{c.pagamento_financeiro === "liquidado" ? "Liquidado" : c.pagamento_financeiro === "cancelado" ? "Cancelado" : c.conta_pagar ? "Pendente" : "Sem título"} · {(c.data_vencimento || c.data).split("-").reverse().join("/")}{c.conta_pagar ? " · #" + c.conta_pagar : ""}</td>
          <td><BotaoAcao acao="editar" type="button" className="secundario" disabled={salvando || excluindo !== undefined} onClick={() => { setId(c.id); setForm({ data: c.data, motorista: c.motorista, fornecedor: c.fornecedor, placa: c.placa, valor_tonelada: c.valor_tonelada, peso_bruto: c.peso_bruto, tara: c.tara, pago: c.pago, observacoes: c.observacoes, data_vencimento: c.data_vencimento }); setAviso(""); window.scrollTo({ top: 0, behavior: "smooth" }); }}>Editar</BotaoAcao> <BotaoAcao acao="excluir" type="button" className="perigo" disabled={salvando || excluindo !== undefined} onClick={() => void excluir(c)}>{excluindo === c.id ? "Excluindo…" : "Excluir"}</BotaoAcao> <BotaoAcao acao="imprimir" type="button" onClick={() => void imprimir(c)}>Romaneio — 2 vias</BotaoAcao></td>
        </tr>)}</tbody></table></div>}
      </>}
    </section>
  </>;
}

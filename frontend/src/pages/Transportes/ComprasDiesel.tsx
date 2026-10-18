import { FormEvent, useEffect, useRef, useState } from "react";
import axios from "axios";
import { CompraDiesel, CompraDieselInput, consultarComprasDiesel, consultarVencimentoDiesel, excluirCompraDiesel, ResumoDiesel, salvarCompraDiesel } from "../../api/diesel";
import { useConfirmacaoCompacta } from "../../components/ConfirmacaoCompacta";
import { BotaoAcao } from "../../components/AcoesContext";
import { useAlteracoesNaoSalvas } from "../../components/AlteracoesNaoSalvas";
import PainelFormulario from "../../components/PainelFormulario";
import { formatarData } from "../../utils/datas";

const novo = (): CompraDieselInput => ({ data: new Date().toLocaleDateString("en-CA"), fornecedor: "", produtor: "", documento: "", tipo: "S10", litros: "", valor_unitario: "", prazo_dias: null, pagamento: "nao_informado", observacoes: "" });
const filtrosVazios = { data_inicio: "", data_fim: "", fornecedor: "", produtor: "", tipo: "", pagamento: "" };
const pagamentos = { nao_informado: "Não informado", pendente: "Pendente", parcial: "Parcial", pago: "Pago" };
const moeda = (valor: string | number) => Number(valor).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
export function erroDiesel(e: unknown) {
  if (axios.isAxiosError(e) && e.response?.data) {
    const dados = e.response.data;
    return typeof dados.detail === "string" ? dados.detail : Object.values(dados).flat().join(" ");
  }
  return "Não foi possível consultar ou salvar o diesel. Tente novamente.";
}

export default function ComprasDiesel() {
  const confirmar = useConfirmacaoCompacta();
  const [form, setForm] = useState(novo);
  const [edicao, setEdicao] = useState<CompraDiesel | null>(null);
  const [filtros, setFiltros] = useState(filtrosVazios), [aplicados, setAplicados] = useState(filtrosVazios);
  const [pagina, setPagina] = useState(1), [revisao, setRevisao] = useState(0);
  const [lista, setLista] = useState<CompraDiesel[]>([]), [total, setTotal] = useState(0);
  const [resumo, setResumo] = useState<ResumoDiesel | null>(null);
  const [carregando, setCarregando] = useState(true), [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState(""), [sucesso, setSucesso] = useState("");
  const [vencimento, setVencimento] = useState("");
  const [erroVencimento, setErroVencimento] = useState("");
  const trava = useRef(false);
  const protecao = useAlteracoesNaoSalvas(form, "compra de diesel", edicao?.id ?? null);
  useEffect(() => {
    setVencimento(""); setErroVencimento("");
    if (!form.data || form.prazo_dias === null) return;
    const controle = new AbortController();
    const timer = window.setTimeout(() => {
      consultarVencimentoDiesel(form.data, form.prazo_dias!, controle.signal).then(data => { if (!controle.signal.aborted) setVencimento(data); }).catch(e => { if (!controle.signal.aborted) setErroVencimento(erroDiesel(e)); });
    }, 200);
    return () => { window.clearTimeout(timer); controle.abort(); };
  }, [form.data, form.prazo_dias]);
  useEffect(() => {
    const controle = new AbortController(); setCarregando(true); setErro(""); setResumo(null); setLista([]);
    consultarComprasDiesel(aplicados, pagina, controle.signal).then(dados => {
      setLista(dados.lista.results); setTotal(dados.lista.count); setResumo(dados.resumo);
    }).catch(e => { if (!controle.signal.aborted) setErro(erroDiesel(e)); }).finally(() => { if (!controle.signal.aborted) setCarregando(false); });
    return () => controle.abort();
  }, [aplicados, pagina, revisao]);
  async function salvar(e: FormEvent) {
    e.preventDefault(); if (trava.current) return;
    trava.current = true; setSalvando(true); setErro(""); setSucesso("");
    try {
      await salvarCompraDiesel(edicao?.id ?? null, form, edicao?.atualizado_em);
      const vazio = novo(); setEdicao(null); setForm(vazio); protecao.marcarSalvo(vazio);
      setSucesso("Compra de diesel salva."); setRevisao(v => v + 1);
    } catch (falha) { setErro(erroDiesel(falha)); }
    finally { trava.current = false; setSalvando(false); }
  }
  async function excluir(item: CompraDiesel) {
    if (trava.current) return;
    if (!(await confirmar({ titulo: "Excluir lançamento de diesel?", mensagem: `${formatarData(item.data)} · ${item.fornecedor} · ${item.tipo} · ${moeda(item.valor_total)}. A compra sairá da consulta e dos totais. Histórico e abastecimentos já registrados serão preservados. Novas consultas de preço usarão somente compras válidas.`, confirmar: "Excluir lançamento", perigo: true }))) return;
    if (trava.current) return;
    trava.current = true; setSalvando(true); setErro(""); setSucesso("");
    try {
      await excluirCompraDiesel(item);
      if (edicao?.id === item.id) { const vazio = novo(); setEdicao(null); setForm(vazio); protecao.marcarSalvo(vazio); }
      setPagina(1); setRevisao(v => v + 1); setSucesso("Lançamento excluído. Histórico e abastecimentos anteriores preservados.");
    } catch (falha) { setErro(erroDiesel(falha)); }
    finally { trava.current = false; setSalvando(false); }
  }
  return <section>
    <h2>Compras de óleo diesel</h2><p>Compras S10 e S500 para o silo. Abastecimentos usam o preço da última compra do mesmo tipo até a data informada.</p>
    {erro && <p className="erro" role="alert">{erro}</p>}{sucesso && <p role="status">{sucesso}</p>}
    <PainelFormulario titulo={edicao ? "Editar compra de diesel" : "Nova compra de diesel"} edicao={edicao?.id}>
      <form className="card formulario" onSubmit={salvar}><div className="transporte-campos">
        <label>Data da compra<input required type="date" value={form.data} onChange={e => setForm({ ...form, data: e.target.value })} /></label>
        <label>Fornecedor<input required maxLength={160} value={form.fornecedor} onChange={e => setForm({ ...form, fornecedor: e.target.value })} /></label>
        <label>Produtor<input required maxLength={160} value={form.produtor} onChange={e => setForm({ ...form, produtor: e.target.value })} /></label>
        <label>Nota / documento<input maxLength={80} value={form.documento} onChange={e => setForm({ ...form, documento: e.target.value })} /></label>
        <label>Diesel<select value={form.tipo} onChange={e => setForm({ ...form, tipo: e.target.value })}><option>S10</option><option>S500</option></select></label>
        <label>Litros<input required type="number" min="0.01" step="0.01" value={form.litros} onChange={e => setForm({ ...form, litros: e.target.value })} /></label>
        <label>Preço por litro (R$)<input required type="number" min="0.0001" step="0.0001" value={form.valor_unitario} onChange={e => setForm({ ...form, valor_unitario: e.target.value })} /></label>
        <label>Prazo em dias corridos<input type="number" min="0" max="32767" step="1" value={form.prazo_dias ?? ""} onChange={e => setForm({ ...form, prazo_dias: e.target.value === "" ? null : Number(e.target.value) })} /></label>
        <label>Vencimento automático<input type="date" readOnly value={vencimento} /></label>
        <label>Pagamento informado na compra<select value={form.pagamento} onChange={e => setForm({ ...form, pagamento: e.target.value })}>{Object.entries(pagamentos).map(([v, nome]) => <option value={v} key={v}>{nome}</option>)}</select></label>
        <label>Observações<textarea value={form.observacoes} onChange={e => setForm({ ...form, observacoes: e.target.value })} /></label>
      </div><p>Vencimento: data da compra + prazo em dias corridos; sábados, domingos e feriados nacionais passam para o próximo dia útil.</p>
      {erroVencimento && <p className="erro" role="alert">{erroVencimento}</p>}
      <p>{form.prazo_dias === null ? "Informe o prazo para gerar a conta a pagar." : "A compra gera uma única conta a pagar. Confirme a baixa no Financeiro."}{edicao?.conta_pagar ? ` Título nº ${edicao.conta_pagar}.` : ""}</p>
      <p>Total: {form.litros && form.valor_unitario ? moeda(Number(form.litros) * Number(form.valor_unitario)) : "Informe litros e preço"}</p>
      <div className="acoes"><BotaoAcao acao={edicao ? "editar" : "cadastrar"} disabled={salvando}>Salvar compra</BotaoAcao><button type="button" className="secundario" disabled={salvando} onClick={() => { void protecao.confirmarDescarte().then(ok => { if (ok) { const vazio = novo(); setEdicao(null); setForm(vazio); protecao.marcarSalvo(vazio); } }); }}>Limpar / cancelar</button></div></form>
    </PainelFormulario>
    <form className="card transporte-filtros" onSubmit={e => { e.preventDefault(); setPagina(1); setAplicados({ ...filtros }); }}>
      {([['data_inicio','Data inicial'],['data_fim','Data final'],['fornecedor','Fornecedor'],['produtor','Produtor']] as const).map(([campo, nome]) => <label key={campo}>{nome}<input type={campo.startsWith('data') ? 'date' : 'text'} value={filtros[campo]} onChange={e => setFiltros({ ...filtros, [campo]: e.target.value })} /></label>)}
      <label>Diesel<select value={filtros.tipo} onChange={e => setFiltros({ ...filtros, tipo: e.target.value })}><option value="">Todos</option><option>S10</option><option>S500</option></select></label>
      <label>Pagamento<select value={filtros.pagamento} onChange={e => setFiltros({ ...filtros, pagamento: e.target.value })}><option value="">Todos</option>{Object.entries(pagamentos).map(([v, nome]) => <option value={v} key={v}>{nome}</option>)}</select></label>
      <button disabled={carregando}>Aplicar filtros</button><button className="secundario" type="button" onClick={() => { setFiltros(filtrosVazios); setAplicados(filtrosVazios); setPagina(1); setRevisao(v => v + 1); }}>Limpar filtros</button>
    </form>
    {carregando && <p role="status">Carregando compras...</p>}
    {resumo && <div className="transporte-indicadores">{[["Compras filtradas", resumo.compras], ["Litros filtrados", Number(resumo.litros).toLocaleString("pt-BR")], ["Valor filtrado", moeda(resumo.valor_total)]].map(([nome, valor]) => <article className="card" key={nome}><span>{nome}</span><strong>{valor}</strong></article>)}</div>}
    {!carregando && resumo && !total && <p>Nenhuma compra encontrada.</p>}
    <div className="transporte-tabela"><table><thead><tr>{['Data','Fornecedor','Produtor','Diesel','Litros','R$/L','Total','Prazo','Vencimento','Pagamento','Nota','Ações'].map(nome => <th key={nome}>{nome}</th>)}</tr></thead><tbody>{lista.map(item => <tr key={item.id}>
      <td>{formatarData(item.data)}</td><td>{item.fornecedor}</td><td>{item.produtor}</td><td>{item.tipo}</td><td>{Number(item.litros).toLocaleString("pt-BR")}</td><td>{moeda(item.valor_unitario)}</td><td>{moeda(item.valor_total)}</td><td>{item.prazo_dias ?? "—"}</td><td>{item.vencimento ? formatarData(item.vencimento) : "—"}</td><td>{pagamentos[item.pagamento as keyof typeof pagamentos]}</td><td>{item.documento || "—"}</td><td><BotaoAcao acao="editar" disabled={salvando} onClick={() => { void protecao.confirmarDescarte().then(ok => { if (ok) { setEdicao(item); setForm({ ...item }); protecao.marcarSalvo(item); } }); }}>Editar</BotaoAcao> <BotaoAcao acao="excluir" type="button" className="perigo" disabled={salvando} onClick={() => void excluir(item)}>Excluir lançamento</BotaoAcao></td>
    </tr>)}</tbody></table></div>
    <div className="acoes"><button className="secundario" disabled={pagina <= 1 || carregando} onClick={() => setPagina(p => p - 1)}>Anterior</button><span>Página {pagina} de {Math.max(1, Math.ceil(total / 50))}</span><button className="secundario" disabled={pagina * 50 >= total || carregando} onClick={() => setPagina(p => p + 1)}>Próxima</button></div>
  </section>;
}

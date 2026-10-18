import { FormEvent, useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { api } from "../../api/propriedades";
import { BotaoAcao, useAcoes } from "../../components/AcoesContext";
import "./prestacoes.css";

type Parcela = {numero:number; vencimento:string; dias:number; amortizacao:string; juros:string; prestacao:string; saldo:string};
type Resultado = {financiado:string; juros:string; total_prestacoes:string; total_com_entrada:string; media_prestacoes:string; criterio:string; parcelas:Parcela[]};
const moeda = (v:string) => Number(v).toLocaleString("pt-BR", {style:"currency", currency:"BRL"});
type Parametros = {valor:string; entrada:string; juros_anual:string; parcelas:string; carencia:string; liberacao:string; primeiro_vencimento:string; periodicidade:string};
export function FolhaPrestacoes({campos, resultado, geradoEm}:{campos:Parametros; resultado:Resultado; geradoEm:string}) {
  const data = (v:string) => v.split("-").reverse().join("/");
  return <article className="prestacoes-folha"><header><small>AGRO-AI-PRO · FINANCEIRO</small><h2>Simulação de prestações — SAC</h2><p>Gerado em {geradoEm} (Brasília) · Valores em reais (R$)</p></header>
    <dl className="prestacoes-parametros">{[["Compra",moeda(campos.valor)],["Entrada",moeda(campos.entrada)],["Juros efetivos anuais",`${campos.juros_anual}%`],["Parcelas com amortização",campos.parcelas],["Carência (só juros)",campos.carencia],["Periodicidade",campos.periodicidade],["Liberação",data(campos.liberacao)],["Primeiro vencimento",data(campos.primeiro_vencimento)]].map(([k,v])=><div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}</dl>
    <p>{resultado.criterio}</p><p>Financiado: <strong>{moeda(resultado.financiado)}</strong> · Juros: {moeda(resultado.juros)} · Prestações: {moeda(resultado.total_prestacoes)} · Total com entrada: <strong>{moeda(resultado.total_com_entrada)}</strong></p><p>Média das prestações: {moeda(resultado.media_prestacoes)}. As prestações variam conforme o saldo.</p>
    <div className="prestacoes-tabela"><table><thead><tr>{["Parcela","Vencimento","Dias","Amortização","Juros","Prestação","Saldo"].map(t=><th key={t}>{t}</th>)}</tr></thead><tbody>{resultado.parcelas.map(p=><tr key={p.numero}><td>{p.numero}</td><td>{data(p.vencimento)}</td><td>{p.dias}</td>{[p.amortizacao,p.juros,p.prestacao,p.saldo].map((v,i)=><td key={i}>{moeda(v)}</td>)}</tr>)}</tbody></table></div><p className="prestacoes-nota">Simulação informativa. Não representa contrato nem cria lançamento financeiro. Tarifas, seguros e outros encargos não informados não estão incluídos.</p>
  </article>;
}
export default function CalculoPrestacoes() {
  const pode = useAcoes();
  const [aberto, setAberto] = useState(false), [geradoEm, setGeradoEm] = useState("");
  const dialogo = useRef<HTMLDialogElement>(null), titulo = useId();
  useEffect(()=>{if(aberto)dialogo.current?.showModal();},[aberto]);
  function imprimir() {
    if (!pode("imprimir")) return;
    document.body.classList.add("imprimindo-comprovante");
    try { window.print(); } finally { document.body.classList.remove("imprimindo-comprovante"); }
  }
  const [campos, setCampos] = useState({valor:"", entrada:"0", juros_anual:"0", parcelas:"5", carencia:"0", liberacao:"", primeiro_vencimento:"", periodicidade:"anual"});
  const [resultado, setResultado] = useState<Resultado | null>(null), [erro, setErro] = useState(""), [ocupado, setOcupado] = useState(false);
  async function simular(e:FormEvent) {
    e.preventDefault(); setOcupado(true); setErro(""); setResultado(null);
    try { setResultado((await api.get<Resultado>("/financeiro/prestacoes/", {params:campos})).data); setGeradoEm(new Date().toLocaleString("pt-BR",{timeZone:"America/Sao_Paulo"})); }
    catch { setErro("Não foi possível simular. Confira valores, entrada, taxa e datas; o vencimento deve ser posterior à liberação."); }
    finally { setOcupado(false); }
  }
  return <section className="card prestacoes-calculo"><h2>Cálculo de prestações — SAC</h2><p>Simulação baseada na planilha PRESTAÇÃO CASE. Não cria dívida, pagamento ou lançamento financeiro.</p><form className="nao-imprimir" onSubmit={simular}><fieldset disabled={ocupado}><div className="transporte-campos">
    {([["valor","Valor da compra (R$)","number"],["entrada","Entrada (R$)","number"],["juros_anual","Juros efetivos anuais (%)","number"],["parcelas","Prestações com amortização","number"],["carencia","Vencimentos iniciais só de juros (carência)","number"],["liberacao","Data de liberação","date"],["primeiro_vencimento","Primeiro vencimento","date"]] as const).map(([k,label,type]) => <label key={k}>{label}<input type={type} required min={k === "valor" || k === "parcelas" ? "1" : type === "number" ? "0" : undefined} max={k === "parcelas" || k === "carencia" ? "360" : undefined} step={k === "parcelas" || k === "carencia" ? "1" : k === "juros_anual" ? "0.0001" : "0.01"} value={campos[k]} onChange={e => {setCampos({...campos,[k]:e.target.value});setResultado(null);}} /></label>)}
    <label>Periodicidade<select value={campos.periodicidade} onChange={e => {setCampos({...campos,periodicidade:e.target.value});setResultado(null);}}><option value="mensal">Mensal</option><option value="semestral">Semestral</option><option value="anual">Anual</option></select></label></div><button type="submit">{ocupado ? "Calculando..." : "Simular prestações"}</button></fieldset></form>
    {erro && <p role="alert" className="erro">{erro}</p>}{resultado && <><div className="acoes nao-imprimir"><BotaoAcao acao="imprimir" type="button" onClick={()=>setAberto(true)}>Conferir e imprimir simulação</BotaoAcao></div><FolhaPrestacoes campos={campos} resultado={resultado} geradoEm={geradoEm}/></>}
    {aberto && resultado && pode("imprimir") && createPortal(<dialog ref={dialogo} className="comprovante-dialogo prestacoes-dialogo card" aria-labelledby={titulo} onCancel={()=>setAberto(false)}><h2 id={titulo} className="nao-imprimir">Prévia de impressão</h2><FolhaPrestacoes campos={campos} resultado={resultado} geradoEm={geradoEm}/><div className="acoes nao-imprimir"><BotaoAcao acao="imprimir" type="button" onClick={imprimir}>Imprimir / salvar PDF</BotaoAcao><button type="button" className="secundario" autoFocus onClick={()=>setAberto(false)}>Fechar</button></div></dialog>,document.body)}
  </section>;
}

import { useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { BotaoAcao, useAcoes } from "../../components/AcoesContext";
import { consultarDemonstrativos, DemonstrativoMotorista } from "../../api/transportes";

const moeda = (valor: string) => Number(valor).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const nomeMes = (mes: string) => new Date(Number(mes.slice(0, 4)), Number(mes.slice(5, 7)) - 1, 1).toLocaleDateString("pt-BR", { month: "long", year: "numeric" });

export function FolhaHolerite({ dados }: { dados: DemonstrativoMotorista }) {
  return <article className="holerite-folha">
    <header><div><small>TRANSPORTES</small><h2>Demonstrativo de remuneração</h2><p>Salário e comissão do motorista</p></div><strong>{nomeMes(dados.competencia)}</strong></header>
    <section className="holerite-identificacao"><span>Motorista<strong>{dados.motorista}</strong></span><span>Competência<strong>{dados.competencia.slice(5)}/{dados.competencia.slice(0, 4)}</strong></span></section>
    <table className="holerite-valores"><thead><tr><th>Descrição</th><th>Referência</th><th>Vencimentos</th></tr></thead><tbody>
      <tr><td>Salário</td><td>Valor cadastrado no mês</td><td>{moeda(dados.salario)}</td></tr>
      <tr><td>Comissão</td><td>Transportes e fretes conferidos</td><td>{moeda(dados.comissao)}</td></tr>
    </tbody></table>
    <div className="holerite-total"><span>Total de salário e comissão</span><strong>{moeda(dados.total)}</strong></div>
    {Number(dados.comissao_fretes ?? "0") > 0 && <p>Comissão manual de cargas e vendas incluída no total: <strong>{moeda(dados.comissao_fretes ?? "0")}</strong>.</p>}
    <h3>Detalhamento por placa</h3><div className="holerite-detalhes"><table><thead><tr><th>Placa</th><th>Salário</th><th>Base da comissão</th><th>Percentual de Transportes</th><th>Fretes conferidos</th><th>Comissão total</th></tr></thead><tbody>{dados.itens.map(item => <tr key={item.id}><td>{item.placa}</td><td>{moeda(item.salario)}</td><td>{item.comissao_percentual === null ? "—" : moeda(item.base_comissao)}</td><td>{item.comissao_percentual === null ? "Valor histórico" : `${Number(item.comissao_percentual).toLocaleString("pt-BR", { maximumFractionDigits: 4 })}%`}</td><td>{moeda(item.comissao_fretes ?? "0")}</td><td>{moeda(item.comissao)}</td></tr>)}</tbody></table></div>
    <p className="holerite-nota">Valores dos cadastros deste mês, somados quando há mais de uma placa. A comissão soma a regra registrada de Transportes e os fretes marcados para adicionar; valores já contabilizados não são somados novamente. Não foram calculados descontos adicionais.</p>
    <footer><p>Data do recebimento: ____ / ____ / ________</p><div className="holerite-assinatura">Assinatura do motorista</div></footer>
  </article>;
}

export default function HoleriteMotorista({ ativo, revisao }: { ativo: boolean; revisao: number }) {
  const pode = useAcoes();
  const [mes, setMes] = useState(() => new Date().toLocaleDateString("en-CA", { timeZone: "America/Sao_Paulo" }).slice(0, 7));
  const [dados, setDados] = useState<DemonstrativoMotorista[] | null>(null);
  const [motorista, setMotorista] = useState("");
  const [erro, setErro] = useState("");
  const [aberto, setAberto] = useState(false);
  const [consulta, setConsulta] = useState(0);
  const dialogo = useRef<HTMLDialogElement>(null);
  const titulo = useId();
  const permitido = pode("imprimir");
  const selecionado = dados?.find(item => item.motorista === motorista && item.competencia === mes);
  useEffect(() => {
    if (!ativo || !permitido) return;
    const controle = new AbortController(); setDados(null); setErro(""); setAberto(false);
    if (!/^\d{4}-(0[1-9]|1[0-2])$/.test(mes)) { setErro("Escolha o mês do demonstrativo."); return; }
    void consultarDemonstrativos(mes, controle.signal).then(resultado => {
      if (!controle.signal.aborted) { setDados(resultado); setMotorista(atual => resultado.some(item => item.motorista === atual) ? atual : ""); }
    }).catch(() => { if (!controle.signal.aborted) setErro("Não foi possível consultar as remunerações. Tente novamente."); });
    return () => controle.abort();
  }, [ativo, permitido, mes, revisao, consulta]);
  useEffect(() => { if (aberto) dialogo.current?.showModal(); }, [aberto]);
  if (!permitido) return <p className="card">A impressão de demonstrativos exige acesso de impressão em Transportes.</p>;
  function imprimir() {
    if (!selecionado) return;
    document.body.classList.add("imprimindo-comprovante");
    try { window.print(); } finally { document.body.classList.remove("imprimindo-comprovante"); }
  }
  return <>
    <section className="card nao-imprimir"><h2>Holerite por motorista</h2><p>Escolha o mês e o motorista para conferir e imprimir salário e comissão.</p><div className="transporte-campos">
      <label>Mês de competência<input type="month" required value={mes} onChange={evento => { setMes(evento.target.value); setMotorista(""); setDados(null); setAberto(false); }} /></label>
      <label>Motorista<select value={motorista} disabled={!dados?.length} onChange={evento => { setMotorista(evento.target.value); setAberto(false); }}><option value="">Selecione o motorista</option>{dados?.map(item => <option key={item.motorista} value={item.motorista}>{item.motorista}</option>)}</select></label>
      <button type="button" className="secundario" onClick={() => setConsulta(valor => valor + 1)}>Atualizar consulta</button>
    </div>{erro ? <p className="erro" role="alert">{erro}</p> : dados === null ? <p role="status">Consultando remunerações...</p> : !dados.length ? <p>Nenhum salário ou comissão cadastrado neste mês.</p> : !selecionado ? <p>Selecione um motorista para visualizar o demonstrativo.</p> : <BotaoAcao acao="imprimir" type="button" onClick={() => setAberto(true)}>Conferir e imprimir holerite</BotaoAcao>}</section>
    {selecionado && <section className="card"><FolhaHolerite dados={selecionado} /></section>}
    {aberto && selecionado && createPortal(<dialog ref={dialogo} className="comprovante-dialogo holerite-dialogo card" aria-labelledby={titulo} onCancel={() => setAberto(false)}><h2 id={titulo} className="nao-imprimir">Prévia do holerite</h2><FolhaHolerite dados={selecionado} /><div className="acoes nao-imprimir"><BotaoAcao acao="imprimir" type="button" onClick={imprimir}>Imprimir / salvar PDF</BotaoAcao><button type="button" className="secundario" autoFocus onClick={() => setAberto(false)}>Fechar</button></div></dialog>, document.body)}
  </>;
}

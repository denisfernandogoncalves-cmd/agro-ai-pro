import { useContext, useEffect, useRef, useState } from "react";
import { EntradaTerceiro, ResumoTerceirosDados, consultarResumoTerceiros, opcoesTerceiros, filtroTerceiro } from "../../api/terceiros";
import { baixarArquivo, erroArquivo } from "../../api/arquivos";
import { AcoesContext, autorizado, BotaoAcao } from "../../components/AcoesContext";
import { formatarNumero } from "../../utils/numeros";

export default function ResumoTerceiros({entradas,ativo}:{entradas:EntradaTerceiro[];ativo:boolean}) {
  const [filtros,setFiltros]=useState({identidade:"",depositante:"",cultura:"",safra:""});
  const [dados,setDados]=useState<ResumoTerceirosDados|null>(null),[erro,setErro]=useState(""),[ocupado,setOcupado]=useState(false),[baixando,setBaixando]=useState(false),[revisao,setRevisao]=useState(0);
  const trava=useRef(false);
  const acesso=useContext(AcoesContext);
  const podeImprimir=acesso===null||autorizado(acesso.acesso,"cargas","imprimir");
  useEffect(()=>{if(!ativo)return;let vigente=true;setOcupado(true);setDados(null);setErro("");void consultarResumoTerceiros(filtros).then(d=>{if(vigente)setDados(d);}).catch(()=>{if(vigente)setErro("Não foi possível consultar o resumo de terceiros. Atualize para tentar novamente.");}).finally(()=>{if(vigente)setOcupado(false);});return()=>{vigente=false;};},[ativo,entradas,filtros,revisao]);
  async function exportar(){if(trava.current)return;trava.current=true;setBaixando(true);setErro("");try{await baixarArquivo("/graos/terceiros/resumo/excel/","resumo-terceiros.xlsx",{...filtros,...filtroTerceiro(filtros.identidade)});}catch(e){setErro(await erroArquivo(e,"Não foi possível exportar o resumo."));}finally{trava.current=false;setBaixando(false);}}
  const opcoes=(campo:"depositante"|"cultura"|"safra")=>[...new Map(entradas.map(i=>[i[campo].trim().toLocaleLowerCase("pt-BR"),i[campo].trim()])).values()].sort((a,b)=>a.localeCompare(b,"pt-BR"));
  return <section className="resumo-terceiros" aria-label="Resumo por terceiro, produto e safra">
    <h4>Resumo por terceiro</h4>
    <div className="painel-filtros"><label>Terceiro do resumo<select value={filtros.identidade} onChange={e=>setFiltros({...filtros,identidade:e.target.value})}><option value="">Todos</option>{opcoesTerceiros(entradas).map(v=><option key={v.chave} value={v.chave}>{v.nome}</option>)}</select></label><label>Produto do resumo<select value={filtros.cultura} onChange={e=>setFiltros({...filtros,cultura:e.target.value})}><option value="">Todos</option>{opcoes("cultura").map(v=><option key={v}>{v}</option>)}</select></label><label>Safra do resumo<select value={filtros.safra} onChange={e=>setFiltros({...filtros,safra:e.target.value})}><option value="">Todas</option>{opcoes("safra").map(v=><option key={v}>{v}</option>)}</select></label><button className="secundario" type="button" disabled={ocupado} onClick={()=>setRevisao(v=>v+1)}>Atualizar resumo</button>{podeImprimir&&<BotaoAcao acao="imprimir" type="button" className="secundario" disabled={ocupado||baixando||!dados} onClick={()=>void exportar()}>{baixando?"Exportando…":"Exportar resumo Excel"}</BotaoAcao>}</div>
    <p>Entradas líquidas vigentes e retiradas ativas, incluindo transferências para CAD/PRO. Cancelamentos e correções preservam o histórico.</p>
    {erro&&<p className="erro" role="alert">{erro}</p>}{ocupado&&<p role="status">Conferindo o resumo…</p>}
    {dados&&<><div className="resumo-peso"><span>Entradas <strong>{formatarNumero(dados.totais.entradas_kg)} kg</strong></span><span>Saídas e transferências <strong>{formatarNumero(dados.totais.saidas_kg)} kg</strong></span><span>Saldo <strong>{formatarNumero(dados.totais.saldo_kg)} kg</strong></span></div><div className="tabela-resumo-terceiros"><table><thead><tr><th>Terceiro</th><th>Produto / safra</th><th>Entradas (kg)</th><th>Saídas (kg)</th><th>Saldo (kg)</th></tr></thead><tbody>{dados.itens.map((i,indice)=><tr key={indice}><td>{i.depositante}<small>{i.terceiro?`Cadastro #${i.terceiro}`:`Recebimento #${i.entrada_legada} sem vínculo`}</small><small>{i.recebimentos} recebimentos ativos · {i.cancelados} cancelados</small></td><td>{i.cultura} / {i.safra}</td><td>{formatarNumero(i.entradas_kg)}</td><td>{formatarNumero(i.saidas_kg)}<small>Transferido para CAD/PRO: {formatarNumero(i.transferencias_kg)} kg</small></td><td><strong>{formatarNumero(i.saldo_kg)}</strong></td></tr>)}</tbody></table></div>{!dados.itens.length&&<p>Nenhum recebimento para os filtros escolhidos.</p>}</>}
  </section>;
}

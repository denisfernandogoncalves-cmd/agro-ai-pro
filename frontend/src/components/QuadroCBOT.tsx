import { useEffect, useRef, useState } from "react";
import { consultarInvesting, ReferenciaInvesting } from "../api/mercado";
import { formatarDataHora, idadeDoDado } from "../utils/datas";

const produtos = [{codigo:"soja",nome:"Soja"},{codigo:"milho",nome:"Milho"},{codigo:"trigo",nome:"Trigo Chicago"},{codigo:"dolar",nome:"Dólar USD/BRL"}];
export function precoCBOT(valor:string) {
  return Number(valor).toLocaleString("pt-BR",{minimumFractionDigits:4,maximumFractionDigits:4});
}

export default function QuadroCBOT() {
  const [cotacoes,setCotacoes]=useState<ReferenciaInvesting[]>([]),[erro,setErro]=useState(""),[ocupado,setOcupado]=useState(true);
  const trava=useRef(false),montado=useRef(true);
  async function atualizar(){
    if(trava.current)return;
    trava.current=true;setOcupado(true);
    try{const dados=await consultarInvesting();if(montado.current){setCotacoes(dados.cotacoes);setErro("");}}
    catch{if(montado.current)setErro("Falha ao consultar Investing. Os valores anteriores permanecem com seus horários originais.");}
    finally{trava.current=false;if(montado.current)setOcupado(false);}
  }
  useEffect(()=>{
    montado.current=true;void atualizar();
    const timer=window.setInterval(()=>{if(document.visibilityState==="visible")void atualizar();},60000);
    const visibilidade=()=>{if(document.visibilityState==="visible")void atualizar();};
    document.addEventListener("visibilitychange",visibilidade);
    return()=>{montado.current=false;window.clearInterval(timer);document.removeEventListener("visibilitychange",visibilidade);};
  },[]);
  return <div aria-label="Preços de Chicago e dólar via Investing">
    <p><strong>Chicago · US$/bushel e dólar · R$/US$</strong></p>
    <p><small>Fonte: Investing.com. Consulta automática a cada 60 segundos enquanto a tela está visível; último preço disponível, sujeito ao atraso da fonte.</small></p>
    {erro&&<p role="alert" className="erro">{erro}</p>}
    {ocupado&&<p role="status">Consultando Investing…</p>}
    {produtos.map(p=>{const c=cotacoes.find(i=>i.produto===p.codigo);return <article className="cotacao-resumo" key={p.codigo}><strong>{p.nome}</strong><span>{c?.valor?`${precoCBOT(c.valor)} ${c.unidade}`:"Cotação não disponível"}</span>{c?.cotado_em&&<small>Cotado em {formatarDataHora(c.cotado_em)} · {idadeDoDado(c.cotado_em)}<br/>{c.simbolo} · {p.codigo==="dolar"?"Câmbio de referência USD/BRL; não é dólar turismo.":c.derivado?"Referência derivada (CFD) dos futuros; não é ajuste oficial.":"Futuros de Chicago; não é preço de ajuste oficial."}<br/>{c.atraso_provedor?"Provedor informa atraso. ":"Sem garantia de tempo real. "}{c.mercado_aberto?"Mercado aberto na fonte.":"Mercado fechado na fonte."}<br/>{p.codigo!=="dolar"&&<>Original: {c.valor_original} US¢/bushel ÷ 100.<br/></>}<a href={c.url} target="_blank" rel="noreferrer">Conferir no Investing</a></small>}{c?.erro&&<small role="status" className="erro">{c.erro}</small>}</article>;})}
    <button className="secundario" type="button" disabled={ocupado} onClick={()=>void atualizar()}>Atualizar cotações</button>
    <p><small>Sem assinatura paga. Consultas compartilhadas por até 60 segundos; falhas aguardam cinco minutos antes de nova tentativa. Os horários das cotações não são substituídos pelo horário da consulta.</small></p>
  </div>;
}

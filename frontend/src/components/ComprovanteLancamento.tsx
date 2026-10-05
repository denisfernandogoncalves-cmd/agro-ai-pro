import { useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { BotaoAcao } from "./AcoesContext";
import { salvarArquivo } from "../api/arquivos";
export type DadosComprovante={titulo:string;campos:[string,string][]};

export const estilosDuasVias=`
.folha-duas-vias{box-sizing:border-box;width:190mm;height:276mm;display:grid;grid-template-rows:133mm 10mm 133mm;background:white;color:#111;font:15px/1.2 Arial,sans-serif;text-align:left}
.folha-duas-vias *{box-sizing:border-box}
.via-comprovante{min-height:0;padding:1.5mm 2mm;overflow:visible}
.via-comprovante h3{font-size:1.35em;line-height:1.15;margin:0 0 1mm;color:#111;overflow-wrap:anywhere;min-width:0}
.via-comprovante header{display:flex;align-items:baseline;justify-content:space-between;gap:3mm;margin-bottom:2mm;padding-bottom:2mm;border-bottom:2px solid #245343}
.via-comprovante header strong{white-space:nowrap;font-size:.8em;border:1px solid #708579;padding:1.2mm 2mm;border-radius:3px}
.via-comprovante small{display:block;font-size:.65em;color:#58635d;margin-bottom:3mm}
.via-comprovante dl{display:grid;grid-template-columns:1fr 1fr;gap:2mm 4mm;margin:0}
.via-comprovante dl>div{display:block;padding:1mm 0 1.5mm;border-bottom:1px solid #d6ded9;align-items:start}
.via-comprovante dl>div.campo-largo{grid-column:1/-1;display:block}
.via-comprovante dt{font-weight:600;font-size:.72em;line-height:1.2;color:#57645d;text-transform:uppercase;letter-spacing:.025em;margin:0 0 .7mm;padding-right:2mm;overflow-wrap:anywhere}
.via-comprovante dd{margin:0;font-weight:500;white-space:pre-wrap;overflow-wrap:anywhere}
.via-comprovante .campo-peso dd{font-weight:700;color:#143a2b;font-size:1.12em}
.folha-duas-vias.compacta{line-height:1.1}
.compacta .via-comprovante{padding:1mm 2mm}
.compacta .via-comprovante header{margin-bottom:.5mm;padding-bottom:.3mm}
.compacta .via-comprovante header strong{padding:.3mm 1mm}
.compacta .via-comprovante h3{font-size:1.2em;margin-bottom:0}
.compacta .via-comprovante small{margin-bottom:.5mm}
.compacta .via-comprovante dl{gap:0 4mm}
.compacta .via-comprovante dl>div{display:grid;grid-template-columns:38% 62%;gap:0;padding:.3mm 0}
.compacta .via-comprovante dl>div.campo-largo{display:block}
.compacta .via-comprovante dt{font-size:1em;text-transform:none;letter-spacing:0;margin:0}
.compacta .via-comprovante .campo-peso dd{font-size:1em}
.separacao-vias{display:flex;align-items:center;justify-content:center;border-top:1px dashed #888;margin-top:6mm;font-size:10px;color:#555}
@page comprovante-duas-vias{size:A4 portrait;margin:10mm}
@media print{body.imprimindo-comprovante{margin:0!important;padding:0!important;min-width:0!important}body.imprimindo-comprovante .comprovante-dialogo.duas-vias{page:comprovante-duas-vias;width:190mm!important;height:276mm!important;margin:0!important;padding:0!important;border-radius:0!important;max-height:none!important;overflow:visible!important}body.imprimindo-comprovante .duas-vias>.somente-tela{display:none!important}.folha-duas-vias{page:comprovante-duas-vias;margin:0;break-inside:avoid;break-after:avoid}.duas-vias .folha-duas-vias{display:grid!important}}
`;
export function classeCampoComprovante(k:string,v:string){return `${v.length>120||/observa|propriedades|qualidade|motivo/i.test(k)?"campo-largo":""} ${/peso|bruto|tara|líquido|sacas/i.test(k)?"campo-peso":""}`.trim();}
export function FolhaDuasVias({dados}:{dados:DadosComprovante}){
  return <section className="folha-duas-vias" aria-label="Duas vias na mesma folha A4">{["Via do arquivo","Via do cliente"].map(via=><section className="via-comprovante" key={via}><header><h3>{dados.titulo}</h3><strong>{via}</strong></header><small>AGRO-AI-PRO · Resumo para conferência. Não substitui documento fiscal.</small><dl>{dados.campos.map(([k,v],i)=><div className={classeCampoComprovante(k,v)||undefined} key={i}><dt>{k}</dt><dd>{v||"—"}</dd></div>)}</dl></section>).flatMap((via,indice)=>indice===0?[via,<div className="separacao-vias" key="corte">Recorte entre as vias</div>]:[via])}</section>;
}
export function htmlComprovante(dados:DadosComprovante,duasVias=false,fonte=15){
  const escapar=(v:string)=>v.replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]!));
  const via=(nome:string)=>`<section class="via-comprovante"><header><h3>${escapar(dados.titulo)}</h3><strong>${nome}</strong></header><small>AGRO-AI-PRO · Resumo para conferência. Não substitui documento fiscal.</small><dl>${dados.campos.map(([k,v])=>`<div${classeCampoComprovante(k,v)?` class="${classeCampoComprovante(k,v)}"`:''}><dt>${escapar(k)}</dt><dd>${escapar(v||"—")}</dd></div>`).join("")}</dl></section>`;
  const conteudo=duasVias?`<section class="folha-duas-vias${fonte<=11?" compacta":""}" aria-label="Duas vias na mesma folha A4">${via("Via do arquivo")}<div class="separacao-vias">Recorte entre as vias</div>${via("Via do cliente")}</section>`:`<h1>${escapar(dados.titulo)}</h1><p>AGRO-AI-PRO · Resumo para conferência. Não substitui documento fiscal.</p><table>${dados.campos.map(([k,v])=>`<tr><th>${escapar(k)}</th><td>${escapar(v)}</td></tr>`).join("")}</table>`;
  return `<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'"><title>${escapar(dados.titulo)}</title><style>${duasVias?`${estilosDuasVias}body{margin:0;padding:0}.folha-duas-vias{font-size:${fonte}px}`:"body{font:16px Arial;color:#183c30;max-width:800px;margin:32px auto;padding:16px}table{width:100%;border-collapse:collapse}th,td{text-align:left;border-bottom:1px solid #ccd8d0;padding:10px;overflow-wrap:anywhere}th{width:35%}@page{size:A4;margin:18mm}"}</style></head><body>${conteudo}</body></html>`;
}
export default function ComprovanteLancamento({dados,rotulo="Comprovante",tipoDocumento="comprovante",duasVias=false}:{dados:DadosComprovante;rotulo?:string;tipoDocumento?:string;duasVias?:boolean}){
  const [aberto,setAberto]=useState(false),[erro,setErro]=useState(""),dialogo=useRef<HTMLDialogElement>(null),titulo=useId();
  function ajustarFolha(){
    const folha=dialogo.current?.querySelector<HTMLElement>(".folha-duas-vias");
    if(!folha)return 15;
    for(const fonte of [15,14,13,12,11,10.5,10,9.5]){
      folha.style.fontSize=`${fonte}px`;
      folha.classList.toggle("compacta",fonte<=11);
      if([...folha.querySelectorAll<HTMLElement>(".via-comprovante")].every(via=>via.scrollHeight<=via.clientHeight && via.scrollWidth<=via.clientWidth)) {setErro("");return fonte;}
    }
    setErro("Este conteúdo excede uma folha A4 com fonte legível. Revise as observações antes de imprimir; nenhum dado foi cortado.");return null;
  }
  useEffect(()=>{if(aberto){dialogo.current?.showModal();if(duasVias)ajustarFolha();}},[aberto,duasVias,dados]);
  function imprimir(){if(duasVias&&ajustarFolha()===null)return;document.body.classList.add("imprimindo-comprovante");try{window.print();}finally{document.body.classList.remove("imprimindo-comprovante");}}
  function baixar(){const fonte=duasVias?ajustarFolha():12;if(fonte===null)return;salvarArquivo(new Blob([htmlComprovante(dados,duasVias,fonte)],{type:"text/html;charset=utf-8"}),`${dados.titulo.replace(/[^a-zA-Z0-9-]/g,"-")}.html`);}
  return <><BotaoAcao acao="imprimir" className="secundario" type="button" onClick={e=>{e.stopPropagation();setAberto(true);}}>{rotulo}</BotaoAcao>{aberto&&createPortal(<dialog ref={dialogo} className={`comprovante-dialogo card${duasVias?" duas-vias":""}`} aria-labelledby={titulo} onCancel={e=>{e.preventDefault();setAberto(false);}}>{duasVias?<><style>{estilosDuasVias}</style><h2 className="somente-tela" id={titulo}>Duas vias em uma folha A4</h2><div className="previa-duas-vias"><FolhaDuasVias dados={dados}/></div></>:<><h2 id={titulo}>{dados.titulo}</h2><p>Resumo para conferência. Não substitui documento fiscal.</p><dl>{dados.campos.map(([k,v],i)=><div key={i}><dt>{k}</dt><dd>{v||"—"}</dd></div>)}</dl></>}{erro&&<p role="alert" className="erro somente-tela">{erro}</p>}<div className="acoes nao-imprimir"><button type="button" onClick={imprimir}>Imprimir {tipoDocumento}</button><button type="button" className="secundario" onClick={baixar}>Baixar {tipoDocumento}</button><button autoFocus type="button" className="secundario" onClick={()=>setAberto(false)}>Fechar</button></div></dialog>,document.body)}</>;
}

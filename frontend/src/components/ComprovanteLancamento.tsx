import { useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { BotaoAcao } from "./AcoesContext";
import { baixarArquivo, erroArquivo, salvarArquivo } from "../api/arquivos";
export type DadosComprovante={titulo:string;campos:[string,string][];camposViaArquivo?:[string,string][];modelo?:"romaneio";tipoMovimento?:"entrada"|"saida"};

export const estilosDuasVias=`
.folha-duas-vias{box-sizing:border-box;width:190mm;height:276mm;display:grid;grid-template-rows:133mm 10mm 133mm;background:white;color:#111;font:17px/1.2 Arial,sans-serif;text-align:left}
.folha-duas-vias *{box-sizing:border-box}
.folha-duas-vias .via-comprovante{min-height:0;padding:1.5mm 2mm;overflow:visible;display:flex;flex-direction:column}
.folha-duas-vias .via-comprovante h3{font-size:1.35em;line-height:1.15;margin:0 0 1mm;color:#111;overflow-wrap:anywhere;min-width:0}
.folha-duas-vias .via-comprovante header{display:flex;align-items:baseline;justify-content:space-between;gap:3mm;margin-bottom:2mm;padding-bottom:2mm;border-bottom:2px solid #245343}
.folha-duas-vias .via-comprovante header strong{white-space:nowrap;font-size:.8em;border:1px solid #708579;padding:1.2mm 2mm;border-radius:3px}
.folha-duas-vias .via-comprovante small{display:block;font-size:.65em;color:#58635d;margin-bottom:3mm}
.folha-duas-vias .via-comprovante dl{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1.3mm 4mm;margin:0;flex:1;align-content:space-between;min-height:0}
.folha-duas-vias .via-comprovante dl>div{display:block;padding:.6mm 0 1mm;border-bottom:1px solid #d6ded9;align-items:start}
.folha-duas-vias .via-comprovante dl>div.campo-largo{grid-column:1/-1;display:block}
.folha-duas-vias .via-comprovante dt{font-weight:600;font-size:.72em;line-height:1.2;color:#57645d;text-transform:uppercase;letter-spacing:.025em;margin:0 0 .7mm;padding-right:2mm;overflow-wrap:anywhere}
.folha-duas-vias .via-comprovante dd{margin:0;font-weight:500;white-space:pre-wrap;overflow-wrap:anywhere}
.folha-duas-vias .via-comprovante .campo-peso dd{font-weight:700;color:#143a2b;font-size:1.12em}
.folha-duas-vias .romaneio-modelo{font-family:Arial,sans-serif;font-size:11px;color:#111;padding:2mm 2.5mm;gap:1.5mm}
.folha-duas-vias .romaneio-modelo header{border-bottom:1px solid #111;margin:0;padding:0 0 1mm;gap:2mm}
.folha-duas-vias .romaneio-modelo header h3{font-size:1.3em;margin:0;color:#111}
.folha-duas-vias .romaneio-modelo header strong{border:1px solid #111;border-radius:0;padding:.7mm 1.5mm;font-size:.9em}
.folha-duas-vias .romaneio-modelo .romaneio-tipo{margin-left:auto;font-weight:700;font-size:.9em;letter-spacing:.08em}
.romaneio-modelo-identificacao,.romaneio-modelo-contexto,.romaneio-modelo-painel,.romaneio-modelo-rodape{display:grid;border:1px solid #111}
.romaneio-modelo-identificacao{grid-template-columns:1fr 1fr}
.romaneio-modelo-identificacao .romaneio-modelo-celula:nth-child(odd),.romaneio-modelo-rodape .romaneio-modelo-celula:nth-child(odd){border-right:1px solid #111}
.romaneio-modelo-identificacao .romaneio-modelo-celula:nth-last-child(-n+2){border-bottom:0}
.romaneio-modelo-contexto{border-top:0}
.romaneio-modelo-celula{display:grid;grid-template-columns:minmax(28mm,42%) minmax(0,1fr);min-height:6mm;border-bottom:1px solid #111}
.romaneio-modelo-celula:last-child{border-bottom:0}
.romaneio-modelo-celula strong{padding:1mm 1.3mm;border-right:1px solid #111;font-size:.9em;text-transform:uppercase}
.romaneio-modelo-celula span{padding:1mm 1.3mm;overflow-wrap:anywhere}
.romaneio-modelo-celula.valor-arquivo span{background:#e4e4e4}
.romaneio-modelo-celula.romaneio-modelo-vazia{grid-template-columns:1fr}
.romaneio-modelo-celula.romaneio-modelo-vazia span{border:0;background:#fff}
.romaneio-modelo-painel{grid-template-columns:1fr 1fr;border-top:0}
.romaneio-modelo-pesagem,.romaneio-modelo-qualidade{min-width:0}
.romaneio-modelo-pesagem{border-right:1px solid #111}
.romaneio-modelo-qualidade{display:flex;flex-direction:column}
.romaneio-modelo-qualidade .romaneio-modelo-celula{grid-template-columns:minmax(24mm,42%) minmax(0,1fr)}
.romaneio-modelo-qualidade .romaneio-modelo-celula span{background:#e4e4e4}
.romaneio-modelo-rodape{grid-template-columns:1fr 1fr;border-top:0}
.romaneio-modelo-observacoes{border:1px solid #111;border-top:0;min-height:7mm;padding:1mm 1.3mm}
.romaneio-modelo-observacoes strong,.romaneio-modelo-assinatura strong{display:block;font-size:.9em;text-transform:uppercase}
.romaneio-modelo-assinaturas{display:grid;grid-template-columns:1fr 1fr;border:1px solid #111;border-top:0;min-height:11mm}
.romaneio-modelo-assinatura{padding:1mm 1.3mm;display:flex;align-items:flex-end}
.romaneio-modelo-assinatura:first-child{border-right:1px solid #111}
.folha-duas-vias.compacta{line-height:1.1}
.folha-duas-vias.compacta .via-comprovante{padding:1mm 2mm}
.folha-duas-vias.compacta .via-comprovante header{margin-bottom:.5mm;padding-bottom:.3mm}
.folha-duas-vias.compacta .via-comprovante header strong{padding:.3mm 1mm}
.folha-duas-vias.compacta .via-comprovante h3{font-size:1.2em;margin-bottom:0}
.folha-duas-vias.compacta .via-comprovante small{margin-bottom:.5mm}
.folha-duas-vias.compacta .via-comprovante dl{grid-template-columns:1fr 1fr;gap:0 4mm}
.folha-duas-vias.compacta .via-comprovante dl>div{display:grid;grid-template-columns:38% 62%;gap:0;padding:.3mm 0}
.folha-duas-vias.compacta .via-comprovante dl>div.campo-largo{display:block}
.folha-duas-vias.compacta .via-comprovante dt{font-size:1em;text-transform:none;letter-spacing:0;margin:0}
.folha-duas-vias.compacta .via-comprovante .campo-peso dd{font-size:1em}
.folha-duas-vias.compacta .romaneio-modelo{font-size:9px;gap:.7mm}
.folha-duas-vias.compacta .romaneio-modelo-celula{min-height:4.8mm}
.separacao-vias{display:flex;align-items:center;justify-content:center;border-top:1px dashed #888;margin-top:6mm;font-size:10px;color:#555}
@page comprovante-duas-vias{size:A4 portrait;margin:10mm}
@media print{body.imprimindo-comprovante{margin:0!important;padding:0!important;min-width:0!important}body.imprimindo-comprovante .comprovante-dialogo.duas-vias{page:comprovante-duas-vias;width:190mm!important;height:276mm!important;margin:0!important;padding:0!important;border-radius:0!important;max-height:none!important;overflow:visible!important}body.imprimindo-comprovante .duas-vias>.somente-tela{display:none!important}.folha-duas-vias{page:comprovante-duas-vias;margin:0;break-inside:avoid;break-after:avoid}.duas-vias .folha-duas-vias{display:grid!important}}
`;
export function classeCampoComprovante(k:string,v:string){return `${v.length>120||/observa|propriedades|qualidade|motivo/i.test(k)?"campo-largo":""} ${/peso|bruto|tara|líquido|sacas/i.test(k)?"campo-peso":""}`.trim();}
function valorCampo(campos:[string,string][],nome:string){return campos.find(([chave])=>chave===nome)?.[1]||"—";}
function qualidadeCampos(valor:string){return valor.split(" · ").map(item=>{const separador=item.indexOf(" ");return separador<0?[item,"—"]:[item.slice(0,separador),item.slice(separador+1)];});}
function tituloRomaneio(titulo:string){return titulo.replace(/^Romaneio de entrada de terceiros/i,"ROMANEIO DE ENTRADA DE TERCEIROS").replace(/^Romaneio de entrada/i,"ROMANEIO DE ENTRADA").replace(/^Romaneio de saída/i,"ROMANEIO").replace(/ · Venda.*$/i,"");}
function camposDaVia(dados:DadosComprovante,via:string){return via==="Via do arquivo"&&dados.tipoMovimento!=="entrada"?[...dados.campos,...(dados.camposViaArquivo||[])]:dados.campos;}
function estruturaRomaneio(dados:DadosComprovante,campos:[string,string][],via:string){
  const entrada=dados.tipoMovimento==="entrada";
  const terceiro=campos.some(([nome])=>nome==="Nome do terceiro");
  const campo=(rotulo:string,chave=rotulo,classe="")=>({rotulo,chave,classe});
  return {
    tipo:entrada?"ENTRADA":"SAÍDA",
    identificacao:[campo(entrada?"Origem":"Destinatário",entrada?"Origem":"Destino / comprador"),campo("Data",entrada?"Data da entrada":"Data da saída"),campo("Produto / safra","Cultura / safra"),campo(entrada?"Situação":"Contrato")],
    contexto:campo(entrada?(terceiro?"Nome do terceiro":"Propriedades / CAD/PRO"):"Propriedade / CAD/PRO"),
    pesagem:[...(entrada?[campo("Peso total"),campo("Tara"),campo("Peso bruto do produto")]:[campo("Peso bruto"),campo("Tara")]),campo("Peso líquido"),campo("Sacas/60","Sacas de 60 kg"),...(entrada?[campo("Desconto (%)"),campo("Desconto (kg)")]:[])],
    rodape:entrada?[campo("Romaneio"),campo("Registrado em"),campo("Responsável pelo registro"),campo("Motorista"),campo("Placa"),campo("Armazenagem"),campo(terceiro?"Documento":"Movimento"),...(terceiro?[campo("Saldo atual")]:[])]:[campo("Motorista"),campo("Placa"),campo("Nota do produtor"),campo("Armazenagem"),via==="Via do arquivo"&&valorCampo(campos,"Valor negociado")!=="—"?campo("Valor negociado","Valor negociado","valor-arquivo"):null,campo("Referência")],
    motivo:entrada?valorCampo(campos,"Motivo de cancelamento"):"—",
  };
}
function RomaneioModelo({dados,via}:{dados:DadosComprovante;via:string}){
  const campos=camposDaVia(dados,via);
  const qualidade=qualidadeCampos(valorCampo(campos,"Qualidade"));
  const estrutura=estruturaRomaneio(dados,campos,via);
  const celula=(item:{rotulo:string;chave:string;classe:string}|null,i:number)=>item?<div className={`romaneio-modelo-celula ${item.classe}`.trim()} key={i}><strong>{item.rotulo}</strong><span>{valorCampo(campos,item.chave)}</span></div>:<div aria-hidden="true" className="romaneio-modelo-celula romaneio-modelo-vazia" key={i}><span /></div>;
  return <section className="via-comprovante romaneio-modelo"><header><h3>{tituloRomaneio(dados.titulo)}</h3><span className="romaneio-tipo">{estrutura.tipo}</span><strong>{via}</strong></header><small>AGRO-AI-PRO · Resumo para conferência. Não substitui documento fiscal.</small><div className="romaneio-modelo-identificacao">{estrutura.identificacao.map(celula)}</div><div className="romaneio-modelo-contexto">{celula(estrutura.contexto,0)}</div><div className="romaneio-modelo-painel"><div className="romaneio-modelo-pesagem">{estrutura.pesagem.map(celula)}</div><div className="romaneio-modelo-qualidade">{qualidade.map(([nome,valor],i)=><div className="romaneio-modelo-celula" key={`${nome}-${i}`}><strong>{nome}</strong><span>{valor}</span></div>)}</div></div><div className="romaneio-modelo-rodape">{estrutura.rodape.map(celula)}</div><div className="romaneio-modelo-observacoes"><strong>Observações</strong><span>{valorCampo(campos,"Observações")}</span></div>{estrutura.motivo!=="—"&&<div className="romaneio-modelo-observacoes"><strong>Motivo de cancelamento</strong><span>{estrutura.motivo}</span></div>}<div className="romaneio-modelo-assinaturas"><div className="romaneio-modelo-assinatura"><strong>Assinatura motorista</strong></div><div className="romaneio-modelo-assinatura"><strong>Assinatura do responsável</strong></div></div></section>;
}
export function FolhaDuasVias({dados}:{dados:DadosComprovante}){
  const campos=(via:string)=>camposDaVia(dados,via);
  return <section className="folha-duas-vias" aria-label="Duas vias na mesma folha A4">{["Via do cliente","Via do arquivo"].map(via=>dados.modelo==="romaneio"?<RomaneioModelo dados={dados} via={via} key={via}/>:<section className="via-comprovante" key={via}><header><h3>{dados.titulo}</h3><strong>{via}</strong></header><small>AGRO-AI-PRO · Resumo para conferência. Não substitui documento fiscal.</small><dl>{campos(via).map(([k,v],i)=><div className={classeCampoComprovante(k,v)||undefined} key={i}><dt>{k}</dt><dd>{v||"—"}</dd></div>)}</dl></section>).flatMap((via,indice)=>indice===0?[via,<div className="separacao-vias" key="corte">Recorte entre as vias</div>]:[via])}</section>;
}
export function htmlComprovante(dados:DadosComprovante,duasVias=false,fonte=17){
  const escapar=(v:string)=>v.replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]!));
  const camposParaVia=(nome:string)=>camposDaVia(dados,nome);
  const viaRomaneio=(nome:string)=>{
    const campos=camposParaVia(nome),estrutura=estruturaRomaneio(dados,campos,nome);
    const celula=(item:{rotulo:string;chave:string;classe:string}|null)=>item?`<div class="romaneio-modelo-celula ${item.classe}"><strong>${escapar(item.rotulo)}</strong><span>${escapar(valorCampo(campos,item.chave))}</span></div>`:`<div aria-hidden="true" class="romaneio-modelo-celula romaneio-modelo-vazia"><span></span></div>`;
    const qualidade=qualidadeCampos(valorCampo(campos,"Qualidade")).map(([rotulo,valor])=>`<div class="romaneio-modelo-celula"><strong>${escapar(rotulo)}</strong><span>${escapar(valor)}</span></div>`).join("");
    return `<section class="via-comprovante romaneio-modelo"><header><h3>${escapar(tituloRomaneio(dados.titulo))}</h3><span class="romaneio-tipo">${estrutura.tipo}</span><strong>${escapar(nome)}</strong></header><small>AGRO-AI-PRO · Resumo para conferência. Não substitui documento fiscal.</small><div class="romaneio-modelo-identificacao">${estrutura.identificacao.map(celula).join("")}</div><div class="romaneio-modelo-contexto">${celula(estrutura.contexto)}</div><div class="romaneio-modelo-painel"><div class="romaneio-modelo-pesagem">${estrutura.pesagem.map(celula).join("")}</div><div class="romaneio-modelo-qualidade">${qualidade}</div></div><div class="romaneio-modelo-rodape">${estrutura.rodape.map(celula).join("")}</div><div class="romaneio-modelo-observacoes"><strong>Observações</strong><span>${escapar(valorCampo(campos,"Observações"))}</span></div>${estrutura.motivo!=="—"?`<div class="romaneio-modelo-observacoes"><strong>Motivo de cancelamento</strong><span>${escapar(estrutura.motivo)}</span></div>`:""}<div class="romaneio-modelo-assinaturas"><div class="romaneio-modelo-assinatura"><strong>Assinatura motorista</strong></div><div class="romaneio-modelo-assinatura"><strong>Assinatura do responsável</strong></div></div></section>`;
  };
  const via=(nome:string)=>{const campos=camposParaVia(nome);if(dados.modelo==="romaneio")return viaRomaneio(nome);return `<section class="via-comprovante"><header><h3>${escapar(dados.titulo)}</h3><strong>${nome}</strong></header><small>AGRO-AI-PRO · Resumo para conferência. Não substitui documento fiscal.</small><dl>${campos.map(([k,v])=>`<div${classeCampoComprovante(k,v)?` class="${classeCampoComprovante(k,v)}"`:''}><dt>${escapar(k)}</dt><dd>${escapar(v||"—")}</dd></div>`).join("")}</dl></section>`;};
  const conteudo=duasVias?`<section class="folha-duas-vias${fonte<=11?" compacta":""}" aria-label="Duas vias na mesma folha A4">${via("Via do cliente")}<div class="separacao-vias">Recorte entre as vias</div>${via("Via do arquivo")}</section>`:`<h1>${escapar(dados.titulo)}</h1><p>AGRO-AI-PRO · Resumo para conferência. Não substitui documento fiscal.</p><table>${dados.campos.map(([k,v])=>`<tr><th>${escapar(k)}</th><td>${escapar(v)}</td></tr>`).join("")}</table>`;
  return `<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'"><title>${escapar(dados.titulo)}</title><style>${duasVias?`${estilosDuasVias}body{margin:0;padding:0}.folha-duas-vias{font-size:${fonte}px}`:"body{font:16px Arial;color:#183c30;max-width:800px;margin:32px auto;padding:16px}table{width:100%;border-collapse:collapse}th,td{text-align:left;border-bottom:1px solid #ccd8d0;padding:10px;overflow-wrap:anywhere}th{width:35%}@page{size:A4;margin:18mm}"}</style></head><body>${conteudo}</body></html>`;
}
export default function ComprovanteLancamento({dados,rotulo="Comprovante",tipoDocumento="comprovante",duasVias=false,downloadRomaneio}:{dados:DadosComprovante;rotulo?:string;tipoDocumento?:string;duasVias?:boolean;downloadRomaneio?:{vendaId:number;saidaId:number}|{terceiroId:number}|{cargaId:number}|{retiradaTerceiroId:number}|{transferenciaTerceiroId:number}}){
  const [aberto,setAberto]=useState(false),[erro,setErro]=useState(""),[baixando,setBaixando]=useState(false),dialogo=useRef<HTMLDialogElement>(null),titulo=useId();
  function ajustarFolha(){
    const folha=dialogo.current?.querySelector<HTMLElement>(".folha-duas-vias");
    if(!folha)return 17;
    for(const fonte of [17,16,15,14,13,12,11,10.5,10,9.5]){
      folha.style.fontSize=`${fonte}px`;
      folha.classList.toggle("compacta",fonte<=11);
      if([...folha.querySelectorAll<HTMLElement>(".via-comprovante")].every(via=>via.scrollHeight<=via.clientHeight && via.scrollWidth<=via.clientWidth)) {setErro("");return fonte;}
    }
    setErro("Este conteúdo excede uma folha A4 com fonte legível. Revise as observações antes de imprimir; nenhum dado foi cortado.");return null;
  }
  useEffect(()=>{if(aberto){dialogo.current?.showModal();if(duasVias)ajustarFolha();}},[aberto,duasVias,dados]);
  function imprimir(){if(duasVias&&ajustarFolha()===null)return;document.body.classList.add("imprimindo-comprovante");try{window.print();}finally{document.body.classList.remove("imprimindo-comprovante");}}
  function baixar(){const fonte=duasVias?ajustarFolha():12;if(fonte===null)return;salvarArquivo(new Blob([htmlComprovante(dados,duasVias,fonte)],{type:"text/html;charset=utf-8"}),`${dados.titulo.replace(/[^a-zA-Z0-9-]/g,"-")}.html`);}
  async function baixarRomaneio(formato:"pdf"|"excel"){
    if(!downloadRomaneio)return;
    setBaixando(true);setErro("");
    try{const carga="cargaId" in downloadRomaneio;const terceiro="terceiroId" in downloadRomaneio;const retirada="retiradaTerceiroId" in downloadRomaneio;const transferencia="transferenciaTerceiroId" in downloadRomaneio;const url=transferencia?`/graos/terceiros/transferencias/${downloadRomaneio.transferenciaTerceiroId}/${formato}/`:retirada?`/graos/terceiros/movimentos/${downloadRomaneio.retiradaTerceiroId}/${formato}/`:carga?`/graos/cargas-colhidas/${downloadRomaneio.cargaId}/${formato}/`:terceiro?`/graos/terceiros/entradas/${downloadRomaneio.terceiroId}/${formato}/`:`/comercial/vendas/${downloadRomaneio.vendaId}/entregas/${downloadRomaneio.saidaId}/${formato}/`;const nome=transferencia?`transferencia-terceiro-${downloadRomaneio.transferenciaTerceiroId}`:retirada?`retirada-terceiro-${downloadRomaneio.retiradaTerceiroId}`:carga?`romaneio-carga-${downloadRomaneio.cargaId}`:terceiro?`romaneio-terceiro-${downloadRomaneio.terceiroId}`:`romaneio-venda-${downloadRomaneio.vendaId}-saida-${downloadRomaneio.saidaId}`;await baixarArquivo(url,`${nome}.${formato==="pdf"?"pdf":"xlsx"}`);}
    catch(e){setErro(await erroArquivo(e,"Não foi possível baixar o romaneio. Tente novamente."));}
    finally{setBaixando(false);}
  }
  return <><BotaoAcao acao="imprimir" className="secundario" type="button" onClick={e=>{e.stopPropagation();setAberto(true);}}>{rotulo}</BotaoAcao>{aberto&&createPortal(<dialog ref={dialogo} className={`comprovante-dialogo card${duasVias?" duas-vias":""}`} aria-labelledby={titulo} onCancel={e=>{e.preventDefault();setAberto(false);}}>{duasVias?<><style>{estilosDuasVias}</style><h2 className="somente-tela" id={titulo}>Duas vias em uma folha A4</h2><div className="previa-duas-vias"><FolhaDuasVias dados={dados}/></div></>:<><h2 id={titulo}>{dados.titulo}</h2><p>Resumo para conferência. Não substitui documento fiscal.</p><dl>{dados.campos.map(([k,v],i)=><div key={i}><dt>{k}</dt><dd>{v||"—"}</dd></div>)}</dl></>}{erro&&<p role="alert" className="erro somente-tela">{erro}</p>}<div className="acoes nao-imprimir"><button type="button" onClick={imprimir}>Imprimir {tipoDocumento}</button>{downloadRomaneio?<><button type="button" className="secundario" disabled={baixando} onClick={()=>void baixarRomaneio("pdf")}>{baixando?"Baixando…":"Baixar PDF"}</button><button type="button" className="secundario" disabled={baixando} onClick={()=>void baixarRomaneio("excel")}>Baixar Excel (.xlsx)</button></>:<button type="button" className="secundario" onClick={baixar}>Baixar {tipoDocumento}</button>}<button autoFocus type="button" className="secundario" onClick={()=>setAberto(false)}>Fechar</button></div></dialog>,document.body)}</>;
}

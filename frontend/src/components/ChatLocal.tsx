import { FormEvent, useEffect, useRef, useState } from "react";
import { api } from "../api/propriedades";
import axios from "axios";
type Resposta={resposta:string;modelo:string;aviso:string;evidencia:{resumo:Record<string,string|number>;gerado_em:string;safra:string}};
export default function ChatLocal({propriedade}:{propriedade:string}) {
  const [pergunta,setPergunta]=useState("");const [safra,setSafra]=useState("");
  const [resposta,setResposta]=useState<Resposta|null>(null);const [enviada,setEnviada]=useState("");
  const [ocupado,setOcupado]=useState(false);const [erro,setErro]=useState("");
  const trava=useRef(false);const ativo=useRef(true);
  useEffect(()=>{ativo.current=true;return()=>{ativo.current=false;};},[]);
  async function consultar(e:FormEvent) {
    e.preventDefault();if(trava.current||!pergunta.trim())return;
    trava.current=true;setOcupado(true);setErro("");setResposta(null);setEnviada(pergunta.trim());
    try {const {data}=await api.post<Resposta>("/ai/conversar/",{pergunta:pergunta.trim(),propriedade:propriedade?Number(propriedade):undefined,safra:safra.trim()},{timeout:65000});if(ativo.current)setResposta(data);}
    catch(falha){if(ativo.current)setErro(axios.isAxiosError(falha)&&typeof falha.response?.data?.detail==="string"?falha.response.data.detail:"Não foi possível consultar a IA local. Tente novamente.");}
    finally{trava.current=false;if(ativo.current)setOcupado(false);}
  }
  return <section className="card assistente-conversa" aria-label="IA local gratuita"><h2>Conversa com IA local</h2><p>Modelo executado neste computador, sem API paga ou envio dos dados à nuvem. Cada pergunta consulta os indicadores atuais dos setores permitidos para sua conta e a propriedade selecionada acima. Não executa operações.</p>
    <form onSubmit={e=>void consultar(e)} className="tw:grid tw:gap-3"><label>Safra da conversa<input maxLength={20} value={safra} disabled={ocupado} onChange={e=>{setSafra(e.target.value);setResposta(null);}} placeholder="Todas ou ex.: 2026"/></label><label>Pergunta para IA local<textarea maxLength={500} value={pergunta} disabled={ocupado} onChange={e=>setPergunta(e.target.value)} placeholder="Ex.: O saldo realizado representa lucro?"/></label><button disabled={ocupado||!pergunta.trim()}>{ocupado?"IA local respondendo…":"Perguntar à IA local"}</button></form>
    {erro&&<p className="erro" role="alert">{erro}</p>}
    {resposta&&<div className="assistente-resposta" aria-live="polite"><p><strong>Pergunta:</strong> {enviada}</p><p style={{whiteSpace:"pre-wrap",overflowWrap:"anywhere"}}>{resposta.resposta}</p><p className="executivo-nota">{resposta.aviso} · Modelo: {resposta.modelo} · Consulta: {new Date(resposta.evidencia.gerado_em).toLocaleString("pt-BR")}</p><details><summary>Evidência oficial da resposta</summary><p>Safra: {resposta.evidencia.safra||"Todas"} · Propriedade: {propriedade||"Todas"}</p><dl>{Object.entries(resposta.evidencia.resumo).map(([campo,valor])=><div key={campo}><dt>{campo.replace(/_/g," ")}</dt><dd>{valor}</dd></div>)}</dl></details></div>}
  </section>;
}

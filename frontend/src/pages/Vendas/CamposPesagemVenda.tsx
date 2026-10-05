import { DadosPesagemVenda } from "../../api/vendas";
import { quantidadeContrato } from "../CadastrosAgricolas/ContratosComerciais";

function decimal(valor:string){return /^0(?:,0{1,3})?$/.test(valor.trim())?"0":quantidadeContrato(valor);}
export function liquidoPesagem(bruto:string,tara:string){
  if(!bruto||!tara)return "";
  try{const b=Number(decimal(bruto)),t=Number(decimal(tara));return b>t?(Math.round((b-t)*1000)/1000).toLocaleString("pt-BR",{maximumFractionDigits:3}):"";}catch{return "";}
}
export function payloadPesagem(dados:DadosPesagemVenda){return Object.fromEntries(Object.entries(dados).filter(([k,v])=>["peso_bruto_kg","tara_kg","umidade_percentual","avariados_percentual","quebrados_percentual","ph"].includes(k)&&v!==""&&v!==null&&v!==undefined).map(([k,v])=>[k,decimal(String(v))]));}
export default function CamposPesagemVenda({dados,liquido,alterar}:{dados:DadosPesagemVenda;liquido:string;alterar:(dados:DadosPesagemVenda,liquido:string)=>void}){
  function campo(chave:keyof DadosPesagemVenda,valor:string){const novo={...dados,[chave]:valor};alterar(novo,liquidoPesagem(novo.peso_bruto_kg||"",novo.tara_kg||""));}
  return <fieldset className="pesagem-venda"><legend>Composição do peso</legend><div className="pesagem-venda-grade"><label>Peso bruto (kg)<input required inputMode="decimal" value={dados.peso_bruto_kg||""} onChange={e=>campo("peso_bruto_kg",e.target.value)}/></label><label>Tara (kg)<input required inputMode="decimal" value={dados.tara_kg||""} onChange={e=>campo("tara_kg",e.target.value)}/></label><label>Peso líquido (kg)<input required readOnly value={liquido}/></label></div><small>Peso líquido = peso bruto − tara. Qualidade não gera descontos na venda.</small><div className="pesagem-venda-grade">{([["umidade_percentual","Umidade (%)"],["avariados_percentual","Avariados (%)"],["quebrados_percentual","Quebrados (%)"],["ph","PH"]] as const).map(([chave,rotulo])=><label key={chave}>{rotulo}<input inputMode="decimal" value={dados[chave]||""} onChange={e=>campo(chave,e.target.value)}/></label>)}</div></fieldset>;
}

import { useState } from "react";
import { api } from "../api/propriedades";
type Origem = {tipo:string;numero:number;campos:Record<string,string|number|null>};
export default function OrigemPendencia({pendencia}:{pendencia:number}) {
  const [dados,setDados]=useState<Origem|null>(null),[erro,setErro]=useState(""),[ocupado,setOcupado]=useState(false);
  async function abrir(){if(ocupado)return;setOcupado(true);setErro("");try{setDados((await api.get<Origem>(`/core/pendencias-conferencia/${pendencia}/origem/`)).data);}catch{setErro("Origem não encontrada ou sem permissão. Confira os dados da pendência.");}finally{setOcupado(false);}}
  return <div className="origem-pendencia"><button type="button" disabled={ocupado} onClick={()=>void abrir()}>Abrir registro de origem</button>{erro&&<p role="alert">{erro}</p>}{dados&&<section className="card"><h4>{dados.tipo} #{dados.numero}</h4><p>Dados atuais do registro identificado na pendência; o histórico original permanece preservado.</p><dl>{Object.entries(dados.campos).map(([k,v])=><div key={k}><dt>{k.replace(/_/g," ")}</dt><dd>{v??"Não informado"}</dd></div>)}</dl><button type="button" className="secundario" onClick={()=>setDados(null)}>Fechar registro de origem</button></section>}</div>;
}

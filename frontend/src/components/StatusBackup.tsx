import { useEffect, useState } from "react";
import { api } from "../api/propriedades";
import { formatarDataHora } from "../utils/datas";
type Status={situacao:"em_dia"|"atrasado"|"ausente";backup_em?:string;verificado_em:string|null;identificador:string|null;limite_dias:number};
export default function StatusBackup(){
  const [dados,setDados]=useState<Status|null>(null),[erro,setErro]=useState(""),[revisao,setRevisao]=useState(0),[ocupado,setOcupado]=useState(false);
  useEffect(()=>{let atual=true;setOcupado(true);setErro("");void api.get<Status>("/core/backup-status/").then(r=>{if(atual)setDados(r.data);}).catch(()=>{if(atual){setDados(null);setErro("Não foi possível verificar a situação do backup completo.");}}).finally(()=>{if(atual)setOcupado(false);});return()=>{atual=false;};},[revisao]);
  return <section className="aviso" aria-label="Situação do backup completo"><h3>Backup completo</h3>{ocupado&&<p role="status">Consultando verificação…</p>}{erro&&<p role="alert" className="erro">{erro}</p>}{dados&&<><p role={dados.situacao==="em_dia"?"status":"alert"}><strong>{dados.situacao==="em_dia"?"Backup verificado em dia":dados.situacao==="atrasado"?"Backup atrasado: faça um novo backup verificado":"Nenhum backup completo verificado encontrado"}</strong></p>{dados.verificado_em&&<p>Backup de {formatarDataHora(dados.backup_em)} · última verificação: {formatarDataHora(dados.verificado_em)} · {dados.identificador}</p>}<p>Prazo: {dados.limite_dias} dias. Evidência de verificação de hashes, arquivos e restauração isolada. A consulta não faz nova restauração nem verifica novamente todos os hashes.</p></>}<button type="button" className="secundario" disabled={ocupado} onClick={()=>setRevisao(v=>v+1)}>Atualizar situação do backup</button></section>;
}

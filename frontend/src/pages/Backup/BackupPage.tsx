import { useRef, useState } from "react";
import { baixarArquivo, erroArquivo } from "../../api/arquivos";

export default function BackupPage() {
  const [ocupado,setOcupado] = useState(false), [erro,setErro] = useState(""), [sucesso,setSucesso] = useState("");
  const trava = useRef(false);
  async function exportar() {
    if (trava.current) return;
    trava.current=true; setOcupado(true); setErro(""); setSucesso("");
    try { await baixarArquivo("/core/backup-excel/", `agro-backup-${new Date().toISOString().slice(0,10)}.xlsx`); setSucesso("Arquivo Excel gerado. Confira o download no navegador."); }
    catch (falha) { setErro(await erroArquivo(falha,"Não foi possível gerar o backup em Excel.")); }
    finally {trava.current=false;setOcupado(false);}
  }
  return <section className="card formulario"><h2>Backup em Excel</h2><p>Baixe uma cópia dos dados de negócio, organizada por abas, com índice e quantidade de registros. Inclui os históricos e lançamentos cancelados.</p><p>Disponível somente para administradores. Senhas, tokens, rascunhos e favoritos privados não são incluídos.</p><div className="aviso"><strong>Cópia para consulta</strong><p>O Excel não restaura o sistema. Os documentos são relacionados por nome e hash, sem o conteúdo dos arquivos. Para recuperação completa, mantenha o backup de banco e uploads.</p></div><button type="button" onClick={() => void exportar()} disabled={ocupado}>{ocupado ? "Gerando Excel…" : "Baixar backup em Excel"}</button>{ocupado&&<p role="status">Aguarde a geração do arquivo. O tempo depende da quantidade de registros.</p>}{erro&&<p role="alert" className="erro">{erro}</p>}{sucesso&&<p role="status">{sucesso}</p>}</section>;
}

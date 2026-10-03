import { useEffect, useRef, useState } from "react";
import { api } from "../api/propriedades";
import { baixarArquivo, erroArquivo } from "../api/arquivos";
import { BotaoAcao, useAcoes } from "./AcoesContext";
import { useConfirmacaoCompacta } from "./ConfirmacaoCompacta";
import { formatarData } from "../utils/datas";
import { useAlteracoesNaoSalvas } from "./AlteracoesNaoSalvas";
type Anexo = {id:number;nome:string;tamanho:number;criado_em:string};
type Entidade = "carga" | "venda" | "transferencia" | "financeiro" | "compra" | "faturamento";

export default function AnexosLancamento({entidade,registro}:{entidade:Entidade;registro:number|string}) {
  const pode=useAcoes(), confirmar=useConfirmacaoCompacta();
  const [aberto,setAberto]=useState(false),[itens,setItens]=useState<Anexo[]>([]),[erro,setErro]=useState(""),[ocupado,setOcupado]=useState(false);
  const [selecionado,setSelecionado]=useState<File|null>(null);
  const protecao=useAlteracoesNaoSalvas(selecionado?{nome:selecionado.name,tamanho:selecionado.size,alterado:selecionado.lastModified}:null,"Documento ainda não enviado",`${entidade}:${registro}`);
  const arquivo=useRef<HTMLInputElement>(null), trava=useRef(false), consulta=useRef(0);
  const url=`/core/anexos/${entidade}/${registro}/`;
  const alvoAtual=useRef(url);alvoAtual.current=url;
  async function carregar() {const id=++consulta.current;setOcupado(true);setErro("");try {const {data}=await api.get<Anexo[]>(url);if(id===consulta.current)setItens(data);}catch {if(id===consulta.current)setErro("Não foi possível consultar os documentos.");}finally{if(id===consulta.current)setOcupado(false);}}
  useEffect(()=>{if(aberto)void carregar();return()=>{consulta.current++;};},[aberto,url]);
  useEffect(()=>{setSelecionado(null);protecao.marcarSalvo(null);},[url]);
  async function anexar() {
    const file=selecionado;if(!file||trava.current)return;
    if(file.size>5*1024*1024){setErro("O limite por documento é 5 MB.");return;}
    trava.current=true;setOcupado(true);setErro("");
    try {const form=new FormData();form.append("arquivo",file);await api.post(url,form);if(alvoAtual.current!==url)return;if(arquivo.current)arquivo.current.value="";setSelecionado(null);protecao.marcarSalvo(null);await carregar();}
    catch(falha){setErro(await erroArquivo(falha,"Confira o arquivo: PDF, PNG ou JPEG de até 5 MB."));}
    finally{trava.current=false;setOcupado(false);}
  }
  async function excluir(item:Anexo){if(trava.current||!(await confirmar({titulo:"Excluir documento",mensagem:`Remover ${item.nome} da lista deste lançamento? O histórico do documento será preservado.`,confirmar:"Excluir",perigo:true})))return;trava.current=true;setOcupado(true);setErro("");try{await api.delete(`/core/anexos/arquivo/${item.id}/`);await carregar();}catch{setErro("Não foi possível excluir o documento.");}finally{trava.current=false;setOcupado(false);}}
  async function baixar(item:Anexo){if(trava.current)return;trava.current=true;setOcupado(true);setErro("");try{await baixarArquivo(`/core/anexos/arquivo/${item.id}/`,item.nome);}catch{setErro("Não foi possível baixar o documento.");}finally{trava.current=false;setOcupado(false);}}
  return <details className="anexos-lancamento nao-imprimir" onToggle={e=>setAberto(e.currentTarget.open)}><summary>Documentos do lançamento #{registro}</summary>{aberto&&<div>{erro&&<p className="erro" role="alert">{erro}</p>}{ocupado&&<p role="status">Processando documentos…</p>}{itens.map(item=><div className="anexo-linha" key={item.id}><span>{item.nome}<small>{Math.ceil(item.tamanho/1024)} KB · {formatarData(item.criado_em)}</small></span><button type="button" className="secundario" disabled={ocupado} onClick={()=>void baixar(item)}>Baixar</button><BotaoAcao acao="excluir" type="button" className="perigo" disabled={ocupado} onClick={()=>void excluir(item)}>Excluir</BotaoAcao></div>)}{!ocupado&&!itens.length&&<p>Nenhum documento anexado.</p>}{pode("cadastrar")&&<div className="anexo-envio"><label>Documento (PDF, PNG ou JPEG, até 5 MB)<input ref={arquivo} type="file" accept="application/pdf,image/png,image/jpeg" disabled={ocupado} onChange={e=>setSelecionado(e.target.files?.[0]||null)}/></label><BotaoAcao acao="cadastrar" type="button" disabled={ocupado||!selecionado} motivoBloqueio={!selecionado?"Selecione um documento para enviar.":undefined} onClick={()=>void anexar()}>Anexar documento</BotaoAcao></div>}</div>}</details>;
}

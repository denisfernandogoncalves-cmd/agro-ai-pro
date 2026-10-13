import { useContext, useEffect, useState } from "react";
import { api } from "../api/propriedades";
import { baixarArquivo, erroArquivo } from "../api/arquivos";
import { Modulo } from "../api/usuarios";
import { AcoesContext, autorizado } from "./AcoesContext";
import { enderecoRedeLocal } from "../utils/redeLocal";
import ChecklistSafraSalvo from "./ChecklistSafraSalvo";
import AnexosLancamento from "./AnexosLancamento";
import { useConfirmarSaida } from "./AlteracoesNaoSalvas";
import { version } from "../../package.json";

type Documento = {doc_tipo:string;doc_numero:number;doc_data:string;doc_nome:string;doc_situacao:string;doc_referencia:string;doc_imprimir:boolean};
type Financeiro = {id:number;tipo:string;status:string;descricao:string;valor:string;valor_liquidado:string|null;diferenca:string;data_liquidacao:string|null};
type Consulta = {resultados: (Documento|Financeiro)[];total:number;pagina:number;total_paginas:number;resumo?:{a_menor:string;a_maior:string}};
type Diagnostico = {conexao:string;banco:string;api:string;django:string;verificado_em:string;backup?:{situacao:string;verificado_em:string|null}};
export type AbrirGestao = (modulo: Modulo, filtros?: Record<string,string|number>) => void;
const moeda = (v: unknown) => Number(v||0).toLocaleString("pt-BR",{style:"currency",currency:"BRL"});
function caminho(d: Documento, formato: "pdf"|"excel") {
  const base = {carga:`/graos/cargas-colhidas/${d.doc_numero}`,terceiro:`/graos/terceiros/entradas/${d.doc_numero}`,retirada:`/graos/terceiros/movimentos/${d.doc_numero}`,transferencia:`/graos/terceiros/transferencias/${d.doc_numero}`,entrega:`/comercial/vendas/${d.doc_referencia}/entregas/${d.doc_numero}`}[d.doc_tipo];
  return base ? `${base}/${formato}/` : `/core/anexos/arquivo/${d.doc_numero}/`;
}

export default function CentralGestao({abrir}: {abrir: AbrirGestao}) {
  const contexto = useContext(AcoesContext);
  const confirmarSaida=useConfirmarSaida();
  const pode = (m: Modulo) => autorizado(contexto?.acesso ?? null,m,"consultar");
  const [aba,setAba]=useState(""),[busca,setBusca]=useState(""),[tipo,setTipo]=useState(""),[inicio,setInicio]=useState(""),[fim,setFim]=useState(""),[pagina,setPagina]=useState(1);
  const [aplicados,setAplicados]=useState({busca:"",tipo:"",inicio:"",fim:"",somente_diferencas:true});
  const [somenteDiferencas,setSomenteDiferencas]=useState(true);
  const [dados,setDados]=useState<Consulta|null>(null),[diagnostico,setDiagnostico]=useState<Diagnostico|null>(null),[erro,setErro]=useState(""),[ocupado,setOcupado]=useState(false),[revisao,setRevisao]=useState(0);
  const [ip,setIp]=useState(()=>typeof window!=="undefined"?window.location.hostname:""),[safra,setSafra]=useState("");
  const endereco = enderecoRedeLocal(ip);
  const comandoRede = endereco ? `.\\scripts\\start-rede-local.ps1 -EnderecoServidor ${endereco}` : "";
  useEffect(()=>{
    if(!aba || aba==="checklist") return;
    let atual=true;setErro("");setOcupado(true);setDados(null);setDiagnostico(null);
    const {busca,tipo,inicio,fim,somente_diferencas}=aplicados;
    const params={pagina,busca,somente_diferencas,tipo:aba==="documentos"?tipo:"",...(inicio?{inicio}:{}),...(fim?{fim}:{})};
    const requisicao=aba==="diagnostico" ? api.get<Diagnostico>("/core/diagnostico/") : api.get<Consulta>(`/core/${aba==="documentos"?"documentos":"conferencia-financeira"}/`,{params});
    void requisicao.then(r=>{if(atual){if(aba==="diagnostico")setDiagnostico(r.data as Diagnostico);else setDados(r.data as Consulta);}}).catch(()=>{if(atual)setErro("Não foi possível carregar a conferência. Verifique a conexão e seus acessos.");}).finally(()=>{if(atual)setOcupado(false);});
    return()=>{atual=false;};
  },[aba,pagina,revisao,aplicados]);
  async function trocar(v:string){if(ocupado||v===aba||!(await confirmarSaida()))return;setAba(v);setPagina(1);setDados(null);setErro("");setInicio("");setFim("");setBusca("");setTipo("");setAplicados({busca:"",tipo:"",inicio:"",fim:"",somente_diferencas:true});setSomenteDiferencas(true);}
  async function baixar(d:Documento,formato:"pdf"|"excel") {setOcupado(true);setErro("");try{await baixarArquivo(caminho(d,formato),d.doc_tipo==="anexo"?d.doc_nome:`${d.doc_tipo}-${d.doc_numero}.${formato==="pdf"?"pdf":"xlsx"}`);}catch(e){setErro(await erroArquivo(e,"Não foi possível baixar o documento."));}finally{setOcupado(false);}}
  const etapas: {id:string;texto:string;modulo:Modulo;filtros?:Record<string,string|number>}[]=[
    {id:"saldo",texto:"Conferir saldo físico, compromissos e origem externa",modulo:"relatorios",filtros:{secao:"saldos"}},
    {id:"contagem",texto:"Comparar contagem física com entradas, retiradas e transferências",modulo:"producao-saldos"},
    {id:"vendas",texto:"Conferir contratos e entregas pendentes",modulo:"relatorios",filtros:{secao:"vendas"}},
    {id:"pendencias",texto:"Revisar duplicidades, responsáveis e pendências",modulo:"cargas",filtros:{aba:"terceiros"}},
    {id:"financeiro",texto:"Conferir pagamentos e recebimentos",modulo:"financeiro"},
  ];
  return <section className="card nao-imprimir central-gestao" aria-label="Central de gestão"><h2>Central de gestão</h2><div className="acoes">
    <button className={aba==="documentos"?"":"secundario"} onClick={()=>trocar("documentos")}>Central de documentos</button>
    <button className={aba==="checklist"?"":"secundario"} onClick={()=>trocar("checklist")}>Checklist de safra</button>
    {pode("financeiro")&&<button className={aba==="financeiro"?"":"secundario"} onClick={()=>trocar("financeiro")}>Conferência financeira</button>}
    <button className={aba==="diagnostico"?"":"secundario"} onClick={()=>trocar("diagnostico")}>Diagnóstico e rede local</button>
  </div>
  {(aba==="documentos"||aba==="financeiro")&&<form className="favoritos-campos" onSubmit={e=>{e.preventDefault();if(inicio&&fim&&inicio>fim){setErro("A data final deve ser igual ou posterior à inicial.");return;}setPagina(1);setAplicados({busca,tipo,inicio,fim,somente_diferencas:somenteDiferencas});}}>
    <label>Buscar na central<input type="search" maxLength={160} value={busca} onChange={e=>setBusca(e.target.value)} placeholder={aba==="documentos"?"Número, nome, propriedade ou documento":"Descrição ou parceiro"}/></label>
    {aba==="documentos"&&<label>Tipo de documento<select value={tipo} onChange={e=>setTipo(e.target.value)}><option value="">Todos</option>{[["carga","Carga própria"],["terceiro","Entrada de terceiro"],["retirada","Retirada de terceiro"],["transferencia","Transferência de terceiro"],["entrega","Entrega de venda"],["anexo","Anexo"]].map(([v,n])=><option key={v} value={v}>{n}</option>)}</select></label>}
    {aba==="financeiro"&&<label><input type="checkbox" checked={somenteDiferencas} onChange={e=>setSomenteDiferencas(e.target.checked)}/>Somente liquidados com diferença</label>}
    <label>Desde<input type="date" value={inicio} onChange={e=>setInicio(e.target.value)}/></label><label>Até<input type="date" min={inicio||undefined} value={fim} onChange={e=>setFim(e.target.value)}/></label><button disabled={ocupado}>Consultar central</button>
    <small>Período pela data do documento; na conferência financeira, pela data da liquidação. A paginação usa os filtros da última consulta.</small>
  </form>}
  {ocupado&&<p role="status">Consultando…</p>}{erro&&<p className="erro" role="alert">{erro}</p>}
  {dados&&<><p>{dados.total} registros · página {dados.pagina} de {Math.max(1,dados.total_paginas)}</p>{aba==="financeiro"&&<p>Liquidado a menor: {moeda(dados.resumo?.a_menor)} · a maior: {moeda(dados.resumo?.a_maior)}. Os valores abrangem toda a consulta. Diferenças exigem conferência; não geram ajuste ou saldo pendente automático.</p>}<div className="tabela-responsiva"><table><thead><tr><th>Registro</th><th>Data</th><th>Descrição</th><th>{aba==="documentos"?"Situação / arquivo":"Valores / diferença"}</th></tr></thead><tbody>{dados.resultados.map(i=>"doc_tipo" in i?<tr key={`${i.doc_tipo}-${i.doc_numero}`}><td>{i.doc_tipo} #{i.doc_numero}</td><td>{i.doc_data}</td><td>{i.doc_nome}</td><td><strong className="situacao-documento">{{ativa:"Ativo",cancelada:"Cancelado",substituida:"Substituído"}[i.doc_situacao]||i.doc_situacao}</strong><div className="acoes">{i.doc_tipo==="anexo"?<button disabled={ocupado} onClick={()=>void baixar(i,"pdf")}>Baixar anexo</button>:i.doc_imprimir?<><button disabled={ocupado} onClick={()=>void baixar(i,"pdf")}>PDF</button><button disabled={ocupado} onClick={()=>void baixar(i,"excel")}>Excel</button></>:<small>Download requer permissão de impressão na origem.</small>}</div></td></tr>:<tr key={i.id}><td>#{i.id} · {i.tipo}</td><td>{i.data_liquidacao||"Sem data"}</td><td>{i.descricao}<small>{i.status}</small>{contexto&&<AcoesContext.Provider value={{...contexto,modulo:"financeiro"}}><AnexosLancamento entidade="financeiro" registro={i.id} titulo="Comprovantes deste título" /></AcoesContext.Provider>}</td><td>Título {moeda(i.valor)} · liquidado {i.valor_liquidado===null?"Não informado":moeda(i.valor_liquidado)} · {i.status==="liquidado"?`diferença ${moeda(i.diferenca)}`:"Título ainda não liquidado ou cancelado"}</td></tr>)}</tbody></table></div>{!dados.total&&<p>Nenhum registro encontrado.</p>}<div className="acoes"><button disabled={ocupado||pagina<=1} onClick={()=>setPagina(v=>v-1)}>Anterior</button><button disabled={ocupado||pagina>=dados.total_paginas} onClick={()=>setPagina(v=>v+1)}>Próxima</button></div></>}
  {aba==="checklist"&&<>
    <ChecklistSafraSalvo />
    <h3>Consultas de apoio ao fechamento</h3><label>Safra das consultas<input maxLength={20} value={safra} onChange={e=>setSafra(e.target.value)}/></label>
    <p>Confira propriedade, armazém e produto em cada consulta. Transferências externas não aumentam produção. O checklist salvo é uma revisão, e o fechamento oficial continua separado.</p>
    {etapas.map(e=><div className="acoes" key={e.id}><span>{e.texto}</span>{pode(e.modulo)?<button className="secundario" onClick={()=>abrir(e.modulo,{...e.filtros,...(safra?{safra}: {})})}>Abrir conferência</button>:<small>Solicite acesso ao módulo correspondente.</small>}</div>)}
    {pode("cargas")&&<button onClick={()=>abrir("cargas",{aba:"terceiros"})}>Abrir fechamento de períodos</button>}
  </>}
  {aba==="diagnostico"&&<>
    <h3>Diagnóstico do sistema</h3><p>Versão da interface: {version}</p>
    {diagnostico&&<><p>Conexão: {diagnostico.conexao} · banco: {diagnostico.banco} · API: {diagnostico.api} · Django: {diagnostico.django}</p><p>Verificado em {new Date(diagnostico.verificado_em).toLocaleString("pt-BR")}</p>{diagnostico.backup?<p>Backup: {diagnostico.backup.situacao} · última verificação: {diagnostico.backup.verificado_em?new Date(diagnostico.backup.verificado_em).toLocaleString("pt-BR"):"Não encontrada"}</p>:<p>Detalhes do backup disponíveis ao administrador.</p>}</>}
    <button disabled={ocupado} onClick={()=>setRevisao(v=>v+1)}>Verificar novamente</button>
    <h3>Acesso pela rede local</h3><label>IPv4 privado do computador servidor<input value={ip} maxLength={15} placeholder="192.168.1.176" onChange={e=>setIp(e.target.value)}/></label>
    {endereco?<><p>Endereço para os demais computadores: <a href={`http://${endereco}:5174/`} target="_blank" rel="noreferrer">http://{endereco}:5174/</a></p><p>No servidor, execute no PowerShell aberto na pasta do projeto:</p><pre>{comandoRede}</pre><div className="acoes"><button className="secundario" onClick={()=>void navigator.clipboard.writeText(`http://${endereco}:5174/`).catch(()=>setErro("Copie o endereço exibido acima."))}>Copiar endereço</button><button className="secundario" onClick={()=>void navigator.clipboard.writeText(comandoRede).catch(()=>setErro("Copie o comando exibido acima."))}>Copiar comando de configuração</button></div></>:<p>Informe um IPv4 privado válido (10.x.x.x, 172.16–31.x.x ou 192.168.x.x).</p>}
    <p>Use a mesma rede do servidor e mantenha o login. Se o acesso estiver bloqueado, o administrador deve conferir a regra de firewall para a porta 5174 e a rede privada.</p>
  </>}
  </section>;
}

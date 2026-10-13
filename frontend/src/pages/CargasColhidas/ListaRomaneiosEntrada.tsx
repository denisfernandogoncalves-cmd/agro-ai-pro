import { useEffect, useState } from "react";
import { EntradaTerceiro } from "../../api/terceiros";
import { CargaColhida } from "../../api/cargasColhidas";
import { useConsultaRomaneios } from "../../api/romaneios";
import { formatarData, formatarDataHora, periodoInvertido } from "../../utils/datas";
import ComprovanteLancamento, { DadosComprovante } from "../../components/ComprovanteLancamento";
import { dadosRomaneioTerceiro } from "./romaneioTerceiro";
import { formatarNumero } from "../../utils/numeros";
export type RomaneioEntrada = { id:number; origem:"propria"|"terceiro"; data:string; nome:string; cultura:string; safra:string; placa:string; cadpros?:string[]; peso:string; historico:boolean; dados:DadosComprovante };
const normalizar=(texto:string)=>texto.normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase();
export function consultarRomaneiosEntrada(itens:RomaneioEntrada[],busca:string,origem:string,historico:boolean,filtros:{cultura?:string;terceiro?:string;inicio?:string;fim?:string}={}){
  const termo=normalizar(busca.trim());
  return itens.filter(i=>(!origem||i.origem===origem)&&(!filtros.cultura||i.cultura===filtros.cultura)&&(!filtros.terceiro||(i.origem==="terceiro"&&normalizar(i.nome).includes(normalizar(filtros.terceiro.trim()))))&&(!filtros.inicio||i.data>=filtros.inicio)&&(!filtros.fim||i.data<=filtros.fim)&&(historico||!i.historico)&&(!termo||(/^#?\d+$/.test(termo)?(String(i.id)===termo.replace(/^#/,"")||(!termo.startsWith("#")&&i.cadpros?.includes(termo))):normalizar(`${i.nome} ${i.placa} ${i.cultura} ${i.safra}`).includes(termo)))).sort((a,b)=>b.data.localeCompare(a.data)||b.id-a.id);
}
type RegistroEntrada = {origem:"propria";registro:CargaColhida}|{origem:"terceiro";registro:EntradaTerceiro};
export default function ListaRomaneiosEntrada({revisao,montarCarga,ativo,onContagem}:{revisao:CargaColhida[];montarCarga:(item:CargaColhida)=>RomaneioEntrada;ativo:boolean;onContagem?:(valor:string|undefined)=>void}){
  const [filtros,setFiltros]=useState({cultura:"",terceiro:"",inicio:"",fim:""});
  const [busca,setBusca]=useState(""),[origem,setOrigem]=useState(""),[historico,setHistorico]=useState(false),[pagina,setPagina]=useState(1);
  const periodoInvalido=periodoInvertido(filtros.inicio,filtros.fim);
  const params:Record<string,string|number|boolean>={busca,origem,historico,pagina,cultura:filtros.cultura,terceiro:filtros.terceiro};
  if(filtros.inicio)params.inicio=filtros.inicio;
  if(filtros.fim)params.fim=filtros.fim;
  const {dados,erro,carregando,atualizar}=useConsultaRomaneios<RegistroEntrada>("/graos/cargas-colhidas/romaneios/",params,ativo,revisao,periodoInvalido);
  const resultados:RomaneioEntrada[]=dados?.itens.map(item=>{
    if(item.origem==="propria")return montarCarga(item.registro);
    const i=item.registro;
    return {id:i.id,origem:"terceiro",data:i.data_entrada,nome:i.depositante,cultura:i.cultura,safra:i.safra,placa:i.placa,peso:i.peso_liquido_kg,historico:i.movimentos.some(m=>m.tipo==="entrada"&&m.estornado),dados:dadosRomaneioTerceiro(i)};
  })||[];
  const [culturas,setCulturas]=useState<string[]>([]);
  useEffect(()=>{if(dados?.culturas)setCulturas(dados.culturas);},[dados]);
  useEffect(()=>{onContagem?.(dados ? String(dados.total) : undefined);},[dados,onContagem]);
  function mudarFiltros(novos:typeof filtros){setFiltros(novos);setPagina(1);}
  function limpar(){setBusca("");setOrigem("");setHistorico(false);mudarFiltros({cultura:"",terceiro:"",inicio:"",fim:""});}
  return <section className="card localizador-romaneios nao-imprimir" aria-label="Romaneios de entrada">
    <header><div><h3>Romaneios de entrada</h3><p>Cargas próprias, compartilhadas e de terceiros. Duas vias na mesma folha A4.</p></div><button type="button" className="secundario" disabled={carregando||periodoInvalido} onClick={atualizar}>Atualizar romaneios</button></header>
    <label>Buscar romaneio de entrada<input type="search" maxLength={160} placeholder="Número, nome, propriedade, CAD/PRO ou placa" value={busca} onChange={e=>{setBusca(e.target.value);setPagina(1);}}/></label>
    <details className="romaneios-filtros-avancados"><summary>Filtros de entrada</summary><label>Produto do romaneio<select value={filtros.cultura} onChange={e=>mudarFiltros({...filtros,cultura:e.target.value})}><option value="">Todos</option>{culturas.map(v=><option key={v}>{v}</option>)}</select></label><label>Terceiro do romaneio<input type="search" maxLength={160} value={filtros.terceiro} onChange={e=>mudarFiltros({...filtros,terceiro:e.target.value})}/></label><label>Entrada desde<input type="date" aria-invalid={periodoInvalido} aria-describedby={periodoInvalido?"erro-periodo-entrada":undefined} value={filtros.inicio} onChange={e=>mudarFiltros({...filtros,inicio:e.target.value})}/></label><label>Entrada até<input type="date" aria-invalid={periodoInvalido} aria-describedby={periodoInvalido?"erro-periodo-entrada":undefined} min={filtros.inicio||undefined} value={filtros.fim} onChange={e=>mudarFiltros({...filtros,fim:e.target.value})}/></label><button type="button" className="secundario" onClick={limpar}>Limpar filtros de romaneios</button><label>Origem do romaneio<select value={origem} onChange={e=>{setOrigem(e.target.value);setPagina(1);}}><option value="">Todas as entradas</option><option value="propria">Cargas próprias e compartilhadas</option><option value="terceiro">Terceiros</option></select></label><label className="romaneios-historico"><input type="checkbox" checked={historico} onChange={e=>{setHistorico(e.target.checked);setPagina(1);}}/>Incluir cancelados e substituídos</label></details>
    <p>Filtros ativos: {[busca&&`busca “${busca}”`,filtros.cultura,filtros.terceiro&&`terceiro “${filtros.terceiro}”`,filtros.inicio&&`desde ${formatarData(filtros.inicio)}`,filtros.fim&&`até ${formatarData(filtros.fim)}`,origem==="propria"?"produção própria":origem==="terceiro"?"terceiros":"",historico&&"inclui histórico"].filter(Boolean).join(" · ")||"nenhum; somente entradas ativas"}.</p>
    {periodoInvalido&&<p id="erro-periodo-entrada" role="alert" className="erro">A data final deve ser igual ou posterior à inicial. Corrija o período para consultar.</p>}
    {carregando&&<p role="status">Consultando cargas próprias e entradas de terceiros…</p>}{erro&&<p role="alert" className="erro">{erro}</p>}
    {dados&&<><p>Entrada líquida ativa dos romaneios filtrados, em todas as páginas: <strong>{formatarNumero(dados.peso_ativo_kg)} kg</strong>. Histórico não somado.</p>
    <p>Consulta concluída em {formatarDataHora(dados.consultado_em)}.</p>
    <p role="status">{dados.inicio}–{dados.fim} de {dados.total} romaneios</p>
    <div className="romaneios-resultados">{resultados.map(i=><article className="romaneio-resultado" key={`${i.origem}-${i.id}`}><div className="romaneio-linha"><div className="romaneio-numero"><strong>{i.id}</strong><span>{i.data.split("-").reverse().join("/")}</span></div><div><strong>{i.nome}</strong>{i.historico&&<span className="erro">Cancelado ou substituído — histórico</span>}<span>{i.origem==="terceiro"?"Terceiro":"Carga própria"} · {i.placa||"Sem placa"} · {formatarNumero(i.peso)} kg</span></div><ComprovanteLancamento duasVias downloadRomaneio={i.origem==="terceiro"?{terceiroId:i.id}:{cargaId:i.id}} dados={i.dados} rotulo={`Imprimir ${i.origem==="terceiro"?"terceiro":"carga"} ${i.id}`} tipoDocumento="romaneio"/></div><details className="romaneio-dados"><summary>Detalhes da entrada {i.id}</summary><p>{i.cultura} · {i.safra} · {i.historico?"Cancelado/substituído — histórico":"Ativa"}</p></details></article>)}</div>
    {!resultados.length&&<p>Nenhum romaneio encontrado para esta busca.</p>}
    {dados.paginas>1&&<nav className="acoes" aria-label="Páginas de romaneios de entrada"><button type="button" className="secundario" disabled={dados.pagina===1} onClick={()=>setPagina(dados.pagina-1)}>Anteriores</button><span>Página {dados.pagina} de {dados.paginas}</span><button type="button" className="secundario" disabled={dados.pagina===dados.paginas} onClick={()=>setPagina(dados.pagina+1)}>Próximos</button></nav>}</>}
  </section>;
}

import QuadroCBOT from "../../components/QuadroCBOT";
import { useContext, useEffect, useState } from "react";
import { AcoesContext, autorizado, DestinoConsulta } from "../../components/AcoesContext";
import { Propriedade } from "../../api/propriedades";
import { api } from "../../api/propriedades";
import { CotacaoMercado, ResumoMercado } from "../../api/mercado";
import { PrevisaoClima } from "../../api/clima";
import GraficoMercado from "../Mercado/GraficoMercado";
import { formatarData } from "../../utils/datas";
type Props={propriedades?:Propriedade[];propriedade:string;safra:string;abrir:(d:Omit<DestinoConsulta,"chave">)=>void};
export default function QuadrosPainel({propriedade,safra,abrir,propriedades=[]}:Props){
 const [propriedadeSelecionada,setPropriedadeSelecionada]=useState(propriedade);
 const [periodo,setPeriodo]=useState(180);
 const inicioPeriodo=new Date();inicioPeriodo.setDate(inicioPeriodo.getDate()-periodo);
 const dataInicioPeriodo=inicioPeriodo.toLocaleDateString("sv-SE");
 const propriedadeClima=propriedade || propriedadeSelecionada;
 const contexto=useContext(AcoesContext), mercado=!!contexto&&autorizado(contexto.acesso,"mercado","consultar"), clima=!!contexto&&autorizado(contexto.acesso,"clima","consultar");
 const [resumos,setResumos]=useState<ResumoMercado[]>([]),[cotacoes,setCotacoes]=useState<CotacaoMercado[]>([]),[previsoes,setPrevisoes]=useState<PrevisaoClima[]>([]),[erroMercado,setErroMercado]=useState(""),[erroClima,setErroClima]=useState(""),[produto,setProduto]=useState("soja"),[carregando,setCarregando]=useState(true);
 useEffect(()=>{let ativo=true;setCarregando(true);setErroMercado("");setErroClima("");setPrevisoes([]);const inicio=new Date();inicio.setDate(inicio.getDate()-180);const tarefas:Promise<unknown>[]=[];
 if(mercado) tarefas.push(Promise.all([api.get<ResumoMercado[]>("/mercado/cotacoes/resumo/"),api.get<CotacaoMercado[]>("/mercado/cotacoes/",{params:{data_inicio:inicio.toLocaleDateString("sv-SE"),ordering:"data,id"}})]).then(([r,c])=>{if(ativo){setResumos(r.data);setCotacoes(c.data);}}).catch(()=>{if(ativo)setErroMercado("Não foi possível consultar o mercado.");}));
 if(clima&&propriedadeClima) tarefas.push(api.get<PrevisaoClima[]>("/clima/previsoes/",{params:{propriedade:propriedadeClima,data_inicio:new Date().toLocaleDateString("sv-SE"),ordering:"data"}}).then(r=>{if(ativo)setPrevisoes(r.data.slice(0,5));}).catch(()=>{if(ativo)setErroClima("Não foi possível consultar a previsão.");}));
 void Promise.all(tarefas).finally(()=>{if(ativo)setCarregando(false);});return()=>{ativo=false;};},[mercado,clima,propriedadeClima]);
 if(!mercado&&!clima)return null;
 return <section className="painel-quadros" aria-label="Mercado e clima da consulta">
 {mercado&&<section className="card"><div className="painel-quadro-titulo"><h2>Preços de mercado</h2><button className="secundario" onClick={()=>abrir({modulo:"mercado",filtros:{}})}>Ver mais</button></div><QuadroCBOT />{resumos.filter(r=>r.produto==="brent").map(r=><article className="cotacao-resumo" key={r.produto}><strong>{r.produto_nome}</strong><span>{Number(r.valor).toLocaleString("pt-BR",{maximumFractionDigits:2})} {r.unidade}</span><small>Indicador mensal FRED/FMI · {formatarData(r.data)}</small></article>)}<small>Grãos CBOT em US$/bushel; Brent mensal mantém US$/barril. Cotações não alteram preços dos contratos.</small></section>}
 {mercado&&<section className="card"><h2>Indicadores mensais — histórico</h2><label>Período<select value={periodo} onChange={e=>setPeriodo(Number(e.target.value))}><option value={30}>Últimos 30 dias</option><option value={90}>Últimos 90 dias</option><option value={180}>Últimos 180 dias</option></select></label><label>Produto<select value={produto} onChange={e=>setProduto(e.target.value)}><option value="soja">Soja</option><option value="milho">Milho</option><option value="trigo">Trigo</option><option value="brent">Brent</option></select></label>{erroMercado?<p>{erroMercado}</p>:<GraficoMercado cotacoes={cotacoes.filter(c=>c.produto===produto && c.data>=dataInicioPeriodo)}/>}<small>Últimos {periodo} dias · {cotacoes.find(c=>c.produto===produto)?.unidade||"Unidade não informada"} · {cotacoes.find(c=>c.produto===produto)?.fonte||"Fonte não informada"}</small></section>}
 {clima&&<section className="card"><div className="painel-quadro-titulo"><h2>Clima da propriedade</h2><button className="secundario" onClick={()=>abrir({modulo:"clima",filtros:{propriedade:propriedadeClima,safra}})}>Ver mais</button></div><small>Previsão atual por propriedade; a safra não altera o período do clima.</small>{!propriedade && <label>Propriedade do clima<select value={propriedadeSelecionada} onChange={e=>setPropriedadeSelecionada(e.target.value)}><option value="">Selecione</option>{propriedades.map(p=><option key={p.id} value={p.id}>{p.nome}</option>)}</select></label>}{!propriedadeClima?<p>Selecione a propriedade neste cartão para consultar o clima.</p>:erroClima?<p role="alert">{erroClima}</p>:<div className="previsao-resumo">{previsoes.map(p=><article key={p.id}><strong>{formatarData(p.data)}</strong><span>{p.temperatura_min??"—"} / {p.temperatura_max??"—"} °C</span><small>{p.chuva_mm??"—"} mm</small><small>{p.condicao}</small></article>)}</div>}{propriedadeClima&&!carregando&&!previsoes.length&&!erroClima&&<p>Previsão não disponível para a propriedade.</p>}{previsoes.length>0&&<small>{previsoes[0].fonte} · Atualizado em {new Date(previsoes[0].atualizado_em).toLocaleString("pt-BR")}</small>}</section>}
 {carregando&&<p role="status">Consultando mercado e clima…</p>}
 </section>;
}

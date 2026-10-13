import { lazy, Suspense, useContext, useEffect, useState } from "react";
import { api, Propriedade } from "../../api/propriedades";
import { Talhao, Pagina } from "../../api/talhoes";
import { AcoesContext, autorizado, DestinoConsulta } from "../../components/AcoesContext";
import { limitesGeometria } from "../../utils/geometria";
const MapaPropriedade = lazy(() => import("../../components/MapaPropriedade"));
type Props = { propriedades:Propriedade[];propriedade:string;safra:string;abrir:(destino:Omit<DestinoConsulta,"chave">)=>void };
export default function MapaPainel({propriedades,propriedade,safra,abrir}:Props) {
  const contexto = useContext(AcoesContext);
  const permitido = !!contexto && autorizado(contexto.acesso,"talhoes","consultar");
  const [talhoes,setTalhoes] = useState<Talhao[]>([]), [total,setTotal] = useState(0), [erro,setErro] = useState(""),[carregando,setCarregando] = useState(false);
  useEffect(()=>{let ativo=true;setTalhoes([]);setErro("");setTotal(0);
    if(permitido && propriedade){setCarregando(true);void api.get<Pagina<Talhao>>("/talhoes/talhoes/",{params:{propriedade,safra,page_size:100,page:1,ordering:"nome,id"}}).then(({data})=>{if(ativo){setTalhoes(data.results);setTotal(data.count);}}).catch(()=>{if(ativo)setErro("Não foi possível consultar os talhões.");}).finally(()=>{if(ativo)setCarregando(false);});}
    else setCarregando(false);
    return()=>{ativo=false;};
  },[permitido,propriedade,safra]);
  if(!permitido)return null;
  const p = propriedades.find(item=>String(item.id)===propriedade);
  const geometrias = talhoes.flatMap(t=>t.geometria_geojson?[t.geometria_geojson]:[]);
  const geometria = geometrias.length ? {type:"MultiPolygon" as const,coordinates:geometrias.flatMap(g=>g.type==="Polygon"?[g.coordinates]:g.coordinates)} : p?.geometria_geojson;
  const limites = geometria ? limitesGeometria(geometria) as [[number,number],[number,number]] : null;
  const latitude = limites ? (limites[0][0]+limites[1][0])/2 : p?.latitude == null ? NaN : Number(p.latitude);
  const longitude = limites ? (limites[0][1]+limites[1][1])/2 : p?.longitude == null ? NaN : Number(p.longitude);
  return <section className="card painel-mapa"><div className="painel-quadro-titulo"><div><h2>Mapa dos talhões</h2><p>{p?.nome || "Selecione uma propriedade no filtro do painel"}{safra?` · ${safra}`:""}</p></div><button className="secundario" onClick={()=>abrir({modulo:"talhoes",filtros:{propriedade,safra}})}>Ver talhões</button></div>
    {erro?<p role="alert">{erro}</p>:carregando?<p role="status">Carregando talhões…</p>:p&&Number.isFinite(latitude)&&Number.isFinite(longitude)?<Suspense fallback={<p>Carregando mapa…</p>}><MapaPropriedade latitude={latitude} longitude={longitude} nome={p.nome} geometria={geometria} talhoes={talhoes}/></Suspense>:<p className="vazio">{p?"Coordenadas ou polígonos ainda não cadastrados.":"O mapa acompanha a propriedade e a safra aplicadas."}</p>}
    {p&&!carregando&&!erro&&<small>{talhoes.length} de {total} talhões · {geometrias.length} com polígonos · contornos verdes identificam os cadastros, sem dados de vigor vegetativo.{total>100?" Prévia limitada aos primeiros 100; consulte o módulo para ver todos.":""}</small>}
  </section>;
}

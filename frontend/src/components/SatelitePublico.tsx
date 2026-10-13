import { useState } from "react";
import { CircleMarker, MapContainer, Popup, WMSTileLayer } from "react-leaflet";
import { api } from "../api/propriedades";
import type { WMSParams } from "leaflet";

type Camada = { camada:string; titulo:string; data:string; resolucao:string; periodo:string };
type Catalogo = { fonte:string; url:string; camadas:Camada[] };
export default function SatelitePublico({latitude,longitude,nome}:{latitude:number;longitude:number;nome:string}) {
  const [catalogo,setCatalogo]=useState<Catalogo|null>(null);
  const [indice,setIndice]=useState(0);
  const [carregando,setCarregando]=useState(false);
  const [erro,setErro]=useState("");
  const [falhaMapa,setFalhaMapa]=useState(false);
  async function abrir() {
    setCarregando(true);setErro("");setFalhaMapa(false);
    try {setCatalogo((await api.get<Catalogo>("/clima/satelite/")).data);}
    catch {setErro("Não foi possível consultar as camadas públicas da NASA. Tente novamente.");}
    finally {setCarregando(false);}
  }
  const camada=catalogo?.camadas[indice];
  return <section className="card"><h2>Satélite e NDVI públicos</h2><p>Imagens regionais NASA/MODIS de 250 m. NDVI é uma composição de 16 dias; não mede sozinho a condição de um talhão nem a produtividade. Nuvens, atraso e pixels sem dados podem limitar a consulta.</p>
    <button type="button" disabled={carregando} onClick={()=>void abrir()}>{carregando?"Consultando NASA…":catalogo?"Atualizar catálogo NASA":"Abrir satélite e NDVI"}</button>
    {erro&&<p className="erro" role="alert">{erro}</p>}
    {catalogo&&camada&&<><label>Camada<select value={indice} onChange={e=>{setIndice(Number(e.target.value));setFalhaMapa(false);}}>{catalogo.camadas.map((c,i)=><option value={i} key={c.camada}>{c.titulo}</option>)}</select></label><p>Fonte: {catalogo.fonte} · Data disponível: {new Date(`${camada.data}T12:00:00Z`).toLocaleDateString("pt-BR",{timeZone:"UTC"})} · Resolução: {camada.resolucao} · Composição: {camada.periodo}.</p>
    <MapContainer key={`${latitude}-${longitude}-${camada.camada}-${camada.data}`} center={[latitude,longitude]} zoom={8} maxZoom={12} className="mapa">
      <WMSTileLayer url={catalogo.url} layers={camada.camada} version="1.1.1" format="image/png" transparent={false} params={{layers:camada.camada,time:camada.data} as WMSParams & {time:string}} attribution='<a href="https://worldview.earthdata.nasa.gov/">NASA GIBS / MODIS</a>' eventHandlers={{tileerror:()=>setFalhaMapa(true)}} />
      <CircleMarker center={[latitude,longitude]} radius={7}><Popup>{nome} · coordenadas cadastradas</Popup></CircleMarker>
    </MapContainer>{falhaMapa&&<p role="status">Uma ou mais imagens não carregaram. A fonte pode estar indisponível ou sem cobertura para esta região/data.</p>}
    {camada.camada==="MODIS_Terra_L3_NDVI_16Day"&&<figure><img style={{maxWidth:"100%",height:"auto"}} src="https://gibs.earthdata.nasa.gov/legends/MODIS_L3_NDVI_H.png" alt="Legenda oficial NASA: escala de cores NDVI"/><figcaption>Legenda oficial NASA/MODIS. NDVI varia de −1 a 1; áreas sem dados não representam vegetação zero.</figcaption></figure>}
    <p className="executivo-nota">Visualização regional, sem média numérica por talhão. Ao abrir, o navegador consulta imagens públicas da região na NASA, sem transmitir nomes ou dados financeiros.</p></>}
  </section>;
}
